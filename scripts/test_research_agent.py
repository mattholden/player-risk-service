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
from src.agents.models import PlayerContext


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_jack_currie():
    """Test research for Matt Phillips - Oxford United."""
    print_header("🔬 Research Agent Test - Matt Phillips")
    
    # Initialize components
    print("\n📦 Initializing...")
    grok_client = GrokClient()
    agent = ResearchAgent(grok_client)
    
    # Create player context
    context = PlayerContext(
        name="Matt Phillips",
        fixture="Oxford United vs Ipswich Town",
        fixture_date=datetime(2025, 11, 28, 19, 45),
        team="Oxford United",
        position="Midfielder"
    )
    
    print(f"\n🎯 Target Player:")
    print(f"   Name: {context.name}")
    print(f"   Team: {context.team}")
    print(f"   Position: {context.position}")
    print(f"   Fixture: {context.fixture}")
    print(f"   Match Date: {context.fixture_date.strftime('%A, %B %d, %Y at %H:%M')}")
    
    # Execute research
    print_header("🔍 Executing Research")
    findings = agent.research_player(context, lookback_days=7)
    
    # Display results
    print_header("📊 Research Findings")
    
    print(f"\n✅ Research completed successfully!")
    print(f"   Timestamp: {findings.search_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Confidence Score: {findings.confidence_score:.2f}")
    
    # Summary
    print(f"\n📝 Summary:")
    print(f"   {findings.summary}")
    
    # Key Findings
    if findings.key_findings:
        print(f"\n🔑 Key Findings ({len(findings.key_findings)}):")
        for i, finding in enumerate(findings.key_findings, 1):
            print(f"   {i}. {finding}")
    else:
        print(f"\n⚠️  No key findings extracted")
    
    # Sources
    if findings.sources:
        print(f"\n📚 Sources ({len(findings.sources)}):")
        for i, source in enumerate(findings.sources, 1):
            print(f"\n   [{i}] {source.title}")
            print(f"       URL: {source.url}")
    else:
        print(f"\n⚠️  No sources found")
    
    # Rate limit status
    print_header("📊 API Usage")
    status = grok_client.get_rate_limit_status()
    print(f"\n   Requests made: {status['requests_made']}")
    print(f"   Remaining: {status['requests_remaining']}/{status['limit']}")
    
    return findings


def test_with_multiple_players():
    """Test with multiple players to see variety of responses."""
    print_header("🔬 Multi-Player Research Test")
    
    grok_client = GrokClient()
    agent = ResearchAgent(grok_client)
    
    players = [
        PlayerContext(
            name="Jack Currie",
            fixture="Oxford United vs Ipswich Town",
            fixture_date=datetime(2025, 11, 28, 19, 45),
            team="Oxford United",
            position="Defender"
        ),
        PlayerContext(
            name="Liam Sercombe",
            fixture="Oxford United vs Ipswich Town",
            fixture_date=datetime(2025, 11, 28, 19, 45),
            team="Oxford United",
            position="Midfielder"
        )
    ]
    
    results = []
    for context in players:
        print(f"\n\n{'='*70}")
        print(f"Researching: {context.name}")
        print('='*70)
        
        findings = agent.research_player(context, lookback_days=7)
        results.append((context, findings))
        
        print(f"\n✅ {context.name}: {len(findings.sources)} sources, confidence {findings.confidence_score:.2f}")
        print(f"   Summary: {findings.summary[:100]}...")
    
    # Summary comparison
    print_header("📊 Multi-Player Summary")
    for context, findings in results:
        print(f"\n   {context.name}:")
        print(f"      Sources: {len(findings.sources)}")
        print(f"      Key Findings: {len(findings.key_findings)}")
        print(f"      Confidence: {findings.confidence_score:.2f}")
    
    return results


def main():
    """Run the test suite."""
    import sys
    
    print("\n" + "="*70)
    print("🚀 Research Agent Testing Suite")
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    try:
        # Test 1: Single player (Jack Currie)
        findings = test_jack_currie()
        
        # Test 2: Multiple players (optional - commented out to save API calls)
        # Uncomment if you want to test multiple players at once
        # print("\n\n")
        # results = test_with_multiple_players()
        
        # Final summary
        print_header("✅ Testing Complete")
        print("\n📝 Next Steps:")
        print("   1. Review the research findings above")
        print("   2. Check if sources are relevant and credible")
        print("   3. Verify confidence scores make sense")
        print("   4. Ready to build Assessment Agent (Agent #2)")
        print("\n   Future: python -m scripts.test_assessment_agent")
        print()
        
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

