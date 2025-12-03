from src.agents.analyst_agent import AnalystAgent
from src.agents.shark_agent import SharkAgent
from src.agents.research_agent import ResearchAgent
from src.clients.grok_client import GrokClient
from src.agents.models import TeamContext
from datetime import datetime
from typing import List
from database import Player, session_scope
from src.agents.models import PlayerAlert
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

    def _save_alerts(self, alerts: List[PlayerAlert]):
        """Save the alerts to the database."""
        with session_scope() as session:
            for alert in alerts:
                player = Player(
                    name=alert.player_name,
                    team=alert.team,
                    fixture=alert.fixture,
                    fixture_date=alert.fixture_date,
                    alert_level=alert.alert_level,
                    description=alert.description,
                    created_at=datetime.now()
                )
                session.add(player)
            session.commit()


    def _print_alerts(self, alerts: List[PlayerAlert]):
        """Print the alerts to the console."""
        for alert in alerts:
            print(f"Player: {alert.player_name}")
            print(f"Alert Level: {alert.alert_level}")
            print(f"Description: {alert.description}")
            print("-"*70)

if __name__ == "__main__":
    pipeline = AgentPipeline()
    alerts = pipeline.run("Arsenal vs Brentford", datetime(2025, 12, 3, 19, 45))
    pipeline._save_alerts(alerts)
    pipeline._print_alerts(alerts)