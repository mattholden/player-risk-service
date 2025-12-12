from src.agents.analyst_agent import AnalystAgent
from src.agents.shark_agent import SharkAgent
from src.agents.research_agent import ResearchAgent
from src.clients.grok_client import GrokClient
from src.agents.models import TeamContext, PlayerAlert
from datetime import datetime
from typing import List
from database import AlertService
class AgentPipeline:
    """
    Pipeline that orchestrates the agents.
    """
    def __init__(self):
        """
        Initialize the pipeline.
        """
        self.grok_client = GrokClient()
        self.analyst_agent = AnalystAgent(self.grok_client)
        self.shark_agent = SharkAgent(self.grok_client)
        self.research_agent = ResearchAgent(self.grok_client)
        self.alert_service = AlertService()

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
        """
        alerts = []
        for context in self._generate_team_contexts(fixture, fixture_date):
            research_agent_response = self.research_agent.research_team(context).findings['description']
            analyst_agent_response = self.analyst_agent.analyze_injury_news(context, research_agent_response)
            shark_agent_response = self.shark_agent.analyze_player_risk(context, research_agent_response, analyst_agent_response)
            alerts.extend(shark_agent_response)
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