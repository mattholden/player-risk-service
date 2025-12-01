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
    print(f"   Timestamp: {findings.search_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Confidence Score: {findings.confidence_score:.2f}")
    
    # Rate limit status
    print_header("📊 API Usage")
    status = grok_client.get_rate_limit_status()
    print(f"\n   Requests made: {status['requests_made']}")
    print(f"   Remaining: {status['requests_remaining']}/{status['limit']}")
    
    return findings


def main():
    """Run the test suite."""
    
    print("\n" + "="*70)
    print("🚀 Research Agent Testing Suite")
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    try:

        context = TeamContext(
            team="Arsenal",
            fixture="Arsenal vs Brentford",
            fixture_date=datetime(2025, 12, 3, 19, 45),
        )
        test_research_agent(context)
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)

