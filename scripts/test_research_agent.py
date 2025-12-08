"""
Test script for Research Agent.

This script tests the full research flow:
1. Initialize Grok client and Research Agent
2. Create PlayerContext for Jack Currie
3. Execute research
4. Display structured findings

Usage:
    python -m scripts.test_research_agent
    make test-research
"""

from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
import json
from typing import List
import traceback

# Load environment variables
load_dotenv()

from src.clients.grok_client import GrokClient
from src.agents.research_agent import ResearchAgent
from src.agents.models import TeamContext


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_research_agent(context: TeamContext):
    """Test research for Matt Phillips - Oxford United."""
    print_header(f"🔬 Research Agent Test - {context.team}")
    
    # Initialize components
    print("\n📦 Initializing...")
    grok_client = GrokClient()
    agent = ResearchAgent(grok_client)
    
    print("\n🎯 Target Player:")
    print(f"   Team: {context.team}")
    print(f"   Fixture: {context.fixture}")
    print(f"   Match Date: {context.fixture_date.strftime('%A, %B %d, %Y at %H:%M')}")
    
    # Execute research
    print_header("🔍 Executing Research")
    findings = agent.research_team(context, lookback_days=7)
    
    print("\n✅ Research completed successfully!")
    print(type(findings.findings))
    print(f"   Findings: {findings.findings}")
    print(f"   Sources: {findings.sources}")
    print(f"   Search Timestamp: {findings.search_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Rate limit status
    print_header("📊 API Usage")
    status = grok_client.get_rate_limit_status()
    print(f"\n   Requests made: {status['requests_made']}")
    print(f"   Remaining: {status['requests_remaining']}/{status['limit']}")
    
    return findings.findings['description']


def main(save_responses: bool = False):
    """Run the test suite."""
    
    print("\n" + "="*70)
    print("🚀 Research Agent Testing Suite")
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)

    fixture = "Arsenal vs Brentford"
    fixture_date = datetime(2025, 12, 3, 19, 45)
    
    if save_responses:
        try:
            for context in generate_team_contexts(fixture, fixture_date):
                save_response(test_research_agent(context), f"research_agent_response_{context.team}_{context.opponent}.json")
            print("\n✅ All research completed successfully!")
            return True
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            traceback.print_exc()
            return False
    try:

        context = generate_team_contexts(fixture, fixture_date)[0]
        test_research_agent(context)
        print("\n✅ All research completed successfully!")
        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        traceback.print_exc()
        return False

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

if __name__ == "__main__":
    import sys
    success = main(save_responses=True)
    sys.exit(0 if success else 1)

