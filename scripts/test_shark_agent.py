from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
import json
from typing import List
import traceback

# Load environment variables
load_dotenv()

from src.clients.grok_client import GrokClient
from src.agents.shark_agent import SharkAgent
from src.agents.models import TeamContext, TeamAnalysis

def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def test_shark_agent(context: TeamContext, injury_news: List[str], analyst_agent_response: TeamAnalysis):
    """Test shark agent"""
    print_header(f"🐟 Shark Agent Test - {context.team}")
    print("\n📦 Initializing...")
    grok_client = GrokClient()
    agent = SharkAgent(grok_client)
    return agent.analyze_player_risk(context, injury_news, analyst_agent_response)

def generate_team_contexts(fixture: str, fixture_date: datetime) -> List[TeamContext]:
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

def save_response(response, filename: str):
    output_path = Path("tmp") / filename
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(response, f, indent=2, default=str)
    print(f"💾 Saved to {output_path}")

def load_response(filename: str):
    output_path = Path("tmp") / filename
    with open(output_path, "r") as f:
        return json.load(f)

def main(save_responses: bool = False):
    """Run the test suite."""
    print("\n" + "="*70)
    print("🚀 Shark Agent Testing Suite")
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    fixture = "Arsenal vs Brentford"
    fixture_date = datetime(2025, 12, 3, 19, 45)
    
    if save_responses:
        try:
            for context in generate_team_contexts(fixture, fixture_date):
                team = context.team
                opponent = context.opponent
                analyst_agent_response = load_response(f"analyst_agent_response_{team}_{opponent}.json")
                injury_news = load_response(f"research_agent_response_{team}_{opponent}.json")
                save_response(test_shark_agent(context, injury_news, analyst_agent_response), f"shark_agent_response_{team}_{opponent}.json")
            print("\n✅ All market inefficiencies identified successfully!")
            return True
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            traceback.print_exc()
            return False
    try:
        context = generate_team_contexts(fixture, fixture_date)[0]
        team = context.team
        opponent = context.opponent
        injury_news = load_response(f"research_agent_response_{team}_{opponent}.json")
        analyst_agent_response = load_response(f"analyst_agent_response_{team}_{opponent}.json")
        test_shark_agent(context, injury_news, analyst_agent_response)
        print("\n✅ All market inefficiencies identified successfully!")
        return True
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import sys
    success = main(save_responses=False)
    sys.exit(0 if success else 1)