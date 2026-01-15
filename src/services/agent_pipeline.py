from src.agents.analyst_agent import AnalystAgent
from src.agents.shark_agent import SharkAgent
from src.agents.research_agent import ResearchAgent
from src.clients.grok_client import GrokClient
from src.agents.models import TeamContext, PlayerAlert
from datetime import datetime
from typing import List
from database import AlertService
from src.logging import get_logger
class AgentPipeline:
    """
    Pipeline that orchestrates the agents.
    """
    def __init__(self, run_id: str):
        """
        Initialize the pipeline.
        """
        self.run_id = run_id
        self.logger = get_logger()
        self.grok_client = GrokClient()
        self.analyst_agent = AnalystAgent(self.grok_client)
        self.shark_agent = SharkAgent(self.grok_client)
        self.research_agent = ResearchAgent(self.grok_client)
        self.alert_service = AlertService(run_id=self.run_id)
        self.logger.success("Agent Pipeline Initialized")

    def _generate_team_contexts(self, fixture: str, fixture_date: datetime) -> List[TeamContext]:
        """Generate a team context for a fixture."""
        team_a, team_b = fixture.split(" vs ")
        return [
            TeamContext(
                team=team_a, 
                opponent=team_b, 
                fixture=fixture, 
                fixture_date=fixture_date
                ), 
            TeamContext(
                team=team_b, 
                opponent=team_a, 
                fixture=fixture, 
                fixture_date=fixture_date
                )
            ]

    def run(self, fixture: str, fixture_date: datetime) -> List[PlayerAlert]:
        """
        Run the pipeline.
        
        New flow to prevent duplicate alerts:
        1. Run Research + Analyst for both teams
        2. Run Shark ONCE with combined data from both teams
        
        This prevents duplicate alerts for players who might be mentioned
        in analysis of both teams.
        """
        contexts = self._generate_team_contexts(fixture, fixture_date)
        
        # Step 1 & 2: Run research and analyst for both teams
        team_analyses = []
        for context in contexts:
            self.logger.reseach_agent_processing(context)
            research_response = self.research_agent.research_team(context).findings['description']
            
            self.logger.analyst_agent_processing(context)
            analyst_response = self.analyst_agent.analyze_injury_news(context, research_response)
            
            team_analyses.append({
                'context': context,
                'research': research_response,
                'analyst': analyst_response
            })
        
        self.logger.shark_agent_processing(contexts[0])
        alerts = self.shark_agent.analyze_player_risk_for_fixture(team_analyses)
        
        return alerts

    def run_and_save(self, fixture: str, fixture_date: datetime) -> List[PlayerAlert]:
        """
        Run the pipeline and save alerts to the database.
        
        Args:
            fixture: Fixture string (e.g., "Arsenal vs Brentford")
            fixture_date: Date and time of the fixture
            
        Returns:
            List[PlayerAlert]: Generated alerts (also saved to DB)
        """
        alerts = self.run(fixture, fixture_date)
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