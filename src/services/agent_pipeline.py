from bdb import BdbQuit
from src.agents.analyst_agent import AnalystAgent
from src.agents.shark_agent import SharkAgent
from src.agents.research_agent import ResearchAgent
from src.clients.grok_client import GrokClient
from src.agents.models import (
    TeamContext, PlayerAlert, AgentData, 
    InjuryResearchFindings, TeamAnalysis, AgentResponseError, FixtureUsage, AgentUsage
)
from datetime import datetime
from typing import List, Callable, Any
from database import AlertService
from src.logging import get_logger
from prompts import get_sport_config  # noqa: E402
from typing import Optional
class AgentPipeline:
    """
    Pipeline that orchestrates the agents.
    """
    def __init__(self, run_id: str, sport: str):
        """
        Initialize the pipeline.
        """
        self.sport = sport
        self.run_id = run_id
        self.logger = get_logger()
        self.grok_client = GrokClient()
        self.sport_config = get_sport_config(self.sport)

        self.analyst_agent = AnalystAgent(
            grok_client=self.grok_client, 
            prompts=self.sport_config.analyst
        )

        self.shark_agent = SharkAgent(
            grok_client=self.grok_client, 
            prompts=self.sport_config.shark
        )

        self.research_agent = ResearchAgent(
            grok_client=self.grok_client, 
            prompts=self.sport_config.research
        )

        self.alert_service = AlertService(run_id=self.run_id)
        self.logger.success("Agent Pipeline Initialized")

        self.fixture_usages: List[FixtureUsage] = []
        self._current_fixture_usage: Optional[FixtureUsage] = None

    def _generate_team_contexts(self, agent_data: AgentData) -> List[TeamContext]:
        """Generate a team context for a fixture."""
        team_a, team_b = agent_data.fixture.split(" vs ")
        return [
            TeamContext(
                team=team_a, 
                opponent=team_b, 
                fixture=agent_data.fixture, 
                fixture_date=agent_data.match_time
                ), 
            TeamContext(
                team=team_b, 
                opponent=team_a, 
                fixture=agent_data.fixture, 
                fixture_date=agent_data.match_time
                )
            ]

    def _run_agent_with_retry(
        self,
        agent_name: str,
        agent_fn: Callable[[], Any],
        validator_fn: Callable[[Any], bool],
        max_retries: int = 3
    ) -> Any:
        """
        Run an agent with retry logic and response validation.
        
        Args:
            agent_name: Name of the agent (for logging)
            agent_fn: Callable that executes the agent and returns result
            validator_fn: Callable that validates the result, returns True if valid
            max_retries: Maximum number of retry attempts
            
        Returns:
            The valid agent result
            
        Raises:
            AgentResponseError: If all retries are exhausted without valid response
        """
        last_error = None
        
        for attempt in range(1, max_retries + 1):
            try:
                result = agent_fn()
                
                if validator_fn(result):
                    if attempt > 1:
                        self.logger.success(f"{agent_name} succeeded on attempt {attempt}")
                    return result
                
                # Invalid response - log and continue to retry
                self.logger.warning(
                    f"{agent_name} returned invalid response on attempt {attempt}/{max_retries}"
                )
                last_error = "Invalid response structure"
                
            except Exception as e:
                # Don't retry on deliberate interrupts (Ctrl+C, quit, debugger exit)
                # Note: KeyboardInterrupt and SystemExit don't inherit from Exception,
                # but BdbQuit (debugger quit) does, so we check explicitly
                if isinstance(e, BdbQuit):
                    raise
                self.logger.warning(
                    f"{agent_name} raised exception on attempt {attempt}/{max_retries}: {e}"
                )
                last_error = str(e)
        
        # All retries exhausted
        raise AgentResponseError(agent_name, f"Max retries ({max_retries}) exhausted. Last error: {last_error}")

    def _validate_research_response(self, result: InjuryResearchFindings) -> bool:
        """
        Validate that research agent returned proper findings with description.
        
        Args:
            result: The InjuryResearchFindings from research agent
            
        Returns:
            True if response is valid, False otherwise
        """
        if result is None:
            return False
        if not isinstance(result.findings, dict):
            return False
        if not result.findings.get('description'):
            return False
        return True

    def _validate_analyst_response(self, result: TeamAnalysis) -> bool:
        """
        Validate that analyst agent returned a valid TeamAnalysis.
        
        Args:
            result: The TeamAnalysis from analyst agent
            
        Returns:
            True if response is valid, False otherwise
        """
        if result is None:
            return False
        if not result.team_analysis:  # Empty string or None
            return False
        return True

    def _setup_usage_data(self, fixture: str, match_time: datetime):
        """
        Setup usage data for a fixture.
        """
        self._current_fixture_usage = FixtureUsage(
            fixture=fixture,
            match_time=match_time,
            agent_usages=[],
            start_timestamp=datetime.now()
        )
    def _record_agent_usage(self, agent_name: str, usage: dict, server_side_tool_usage: dict):
        """
        Record agent usage data from Grok response.
        """
        try:
            agent_usage = AgentUsage(
                agent_name=agent_name,
                total_tokens=usage.get('total_tokens'),
                completion_tokens=usage.get('completion_tokens'),
                reasoning_tokens=usage.get('reasoning_tokens'),
                prompt_tokens=usage.get('prompt_tokens'),
                server_side_tool_usage=server_side_tool_usage,
                completion_timestamp=datetime.now()
            )
            self._current_fixture_usage.agent_usages.append(agent_usage)
            self.logger.grok_client_usage(agent_usage)
        except Exception as e:
            self.logger.error(f"Error recording agent usage for {agent_name}: {e}")
            return None

    def _record_fixture_usage(self):
        """
        Record fixture usage data.
        """
        self.fixture_usages.append(self._current_fixture_usage)
        self._current_fixture_usage = None

    def run(self, agent_data: AgentData) -> List[PlayerAlert]:
        """
        Run the pipeline with agent-level retry logic.
        
        Flow:
        1. Run Research Agent for each team (with retry on invalid response)
        2. Run Analyst Agent for each team (with retry on invalid response)
        3. Run Shark Agent once with combined data from both teams
        
        If any agent fails all retries, AgentResponseError is raised,
        which bubbles up to fixture-level retry in pipeline.py.
        """

        agent_data.team_contexts = self._generate_team_contexts(agent_data)
        
        # Step 1 & 2: Run research and analyst for both teams
        team_analyses = []
        self._setup_usage_data(agent_data.fixture, agent_data.match_time)

        for context in agent_data.team_contexts:
            # Research Agent with retry and validation
            self.logger.reseach_agent_processing(context)
            research_result = self._run_agent_with_retry(
                agent_name=f"Research Agent ({context.team})",
                agent_fn=lambda ctx=context: self.research_agent.research_team(ctx),
                validator_fn=self._validate_research_response
            )
            research_response = research_result.findings.get('description')
            self._record_agent_usage(f"Research Agent ({context.team})", research_result.usage, research_result.server_side_tool_usage)

            # Analyst Agent with retry and validation
            self.logger.analyst_agent_processing(context)
            analyst_result = self._run_agent_with_retry(
                agent_name=f"Analyst Agent ({context.team})",
                agent_fn=lambda ctx=context, research=research_response: 
                    self.analyst_agent.analyze_injury_news(ctx, research),
                validator_fn=self._validate_analyst_response
            )
            analyst_response = analyst_result.team_analysis
            self._record_agent_usage(f"Analyst Agent ({context.team})", analyst_result.usage, analyst_result.server_side_tool_usage)
            team_analyses.append({
                'context': context,
                'research': research_response,
                'analyst': analyst_response
            })
        
        self.logger.shark_agent_processing(agent_data.team_contexts[0])
        shark_response = self.shark_agent.analyze_player_risk_for_fixture(team_analyses)
        self._record_agent_usage(f"Shark Agent ({context.fixture})", shark_response.usage, shark_response.server_side_tool_usage)
        self._record_fixture_usage()

        return shark_response.alerts

    def run_and_save(self, agent_data: AgentData) -> List[PlayerAlert]:
        """
        Run the pipeline and save alerts to the database.
        
        Args:
            agent_data: AgentData object
            
        Returns:
            List[PlayerAlert]: Generated alerts (also saved to DB)
        """
        alerts = self.run(agent_data)
        if alerts:
            self.alert_service.save_alerts(alerts)
        return alerts


if __name__ == "__main__":
    import json
    
    pipeline = AgentPipeline()
    alerts = pipeline.run_and_save("Liverpool vs Brighton & Hove Albion", datetime(2025, 12, 13, 00, 00))
    
    # Print as JSON (pretty)
    for alert in alerts:
        print(json.dumps(alert.model_dump(), indent=2, default=str))