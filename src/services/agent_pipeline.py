from src.agents.analyst_agent import AnalystAgent
from src.agents.shark_agent import SharkAgent
from src.agents.research_agent import ResearchAgent
from src.clients.grok_client import GrokClient
from src.agents.models import TeamContext, PlayerAlert, AgentData
from datetime import datetime
from typing import List
from database import AlertService
from src.logging import get_logger
from prompts import get_sport_config  # noqa: E402
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

    def run(self, agent_data: AgentData) -> List[PlayerAlert]:
        """
        Run the pipeline.
        
        New flow to prevent duplicate alerts:
        1. Run Research + Analyst for both teams
        2. Run Shark ONCE with combined data from both teams
        
        This prevents duplicate alerts for players who might be mentioned
        in analysis of both teams.
        """

        agent_data.team_contexts = self._generate_team_contexts(agent_data)
        
        # Step 1 & 2: Run research and analyst for both teams
        team_analyses = []
        for context in agent_data.team_contexts:
            self.logger.reseach_agent_processing(context)
            research_response = self.research_agent.research_team(context).findings['description']
            breakpoint()
            self.logger.analyst_agent_processing(context)
            analyst_response = self.analyst_agent.analyze_injury_news(context, research_response)
            
            team_analyses.append({
                'context': context,
                'research': research_response,
                'analyst': analyst_response
            })
        
        self.logger.shark_agent_processing(agent_data.team_contexts[0])
        alerts = self.shark_agent.analyze_player_risk_for_fixture(team_analyses)
        
        return alerts

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