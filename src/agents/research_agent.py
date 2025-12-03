"""
Research Agent - Searches for player injury news using Grok.

This agent:
1. Takes a TeamContext (name, fixture, date, etc.)
2. Builds an intelligent search prompt
3. Uses Grok's real-time search (X/Twitter + web)
4. Extracts structured findings with source citations
5. Returns ResearchFindings for downstream processing

This is Agent #1 in the two-agent pipeline.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json

from src.clients.grok_client import GrokClient
from src.agents.models import Source, InjuryResearchFindings, TeamContext


class ResearchAgent:
    """
    Agent that researches player injury status using Grok's search capabilities.
    
    This agent is responsible for finding and organizing information, but NOT
    for making risk assessments. That's the job of the Assessment Agent.
    
    Usage:
        agent = ResearchAgent(grok_client)
        context = PlayerContext(
            name="Jack Currie",
            fixture="Oxford United vs Ipswich Town",
            fixture_date=datetime(2025, 11, 28, 19, 45)
        )
        findings = agent.research_player(context)
    """
    
    def __init__(self, grok_client: GrokClient):
        """
        Initialize Research Agent.
        
        Args:
            grok_client: Initialized GrokClient instance
        """
        self.grok_client = grok_client
        print("✅ ResearchAgent initialized")
    
    def research_team(
        self, 
        context: TeamContext,
        lookback_days: int = 14
    ) -> InjuryResearchFindings:
        """
        Research a player's injury status and availability.
        
        Args:
            context: Player context with name, fixture, date, etc.
            lookback_days: How many days back to search for news
            
        Returns:
            InjuryResearchFindings with sources, key findings, and summary
        """
        print(f"\n🔍 Researching: {context.team}")
        print(f"   Fixture: {context.fixture}")
        print(f"   Date: {context.fixture_date.strftime('%B %d, %Y')}")
        
        # Build the search prompt
        user_message = self._build_user_message(context, lookback_days)
        system_message = self._build_system_message()
        print("System message:")
        print(system_message)
        print("User message:")
        print(user_message)
        messages = [system_message, user_message]
        # Execute search via Grok
        try:
            response = self.grok_client.chat_completion(
                messages=messages,
                use_web_search=False,
                use_x_search=True,
                return_citations=True
            )
            # Parse the JSON string into a dictionary
            try:
                content_json = json.loads(response.get('content', '{}'))
                print("\n" + "="*70)
                print("🔍 DEBUG: Parsed JSON Response (dict)")
                print("="*70)
                print(json.dumps(content_json, indent=2))
                print("="*70 + "\n")
            except json.JSONDecodeError as e:
                print(f"⚠️  Failed to parse JSON response: {e}")
                print(f"   Raw content: {response.get('content', '')[:200]}...")
                content_json = {}
            
            return InjuryResearchFindings(
                team_name=context.team,
                fixture=context.fixture,
                findings=content_json,  # Now passing the parsed dictionary
                sources=response.get('sources', []),
                search_timestamp=datetime.now()
            )
            
        except Exception as e:
            print(f"❌ Research failed: {e}")
            # Return empty findings on error
            return InjuryResearchFindings(
                team_name=context.team,
                fixture=context.fixture,
                findings=[],
                sources=[],
                search_timestamp=datetime.now()
            )
    
    def _build_user_message(self, context: TeamContext, lookback_days: int) -> str:
        """
        Build a user message for the Grok API.
        
        Args:
            context: Player context
            lookback_days: How many days back to search
            
        Returns:
            Formatted prompt string
        """
        # Calculate the date range
        fixture_date_str = context.fixture_date.strftime("%B %d, %Y")
        search_from = (datetime.now() - timedelta(days=lookback_days)).strftime("%B %d, %Y")
        
        # Simple, natural prompt - explicitly request web search
        prompt = f"""
Search for injury news about {context.team} ahead of their match against {context.fixture} on {fixture_date_str}.

Focus on:
- Squad availability and fitness updates
- Players ruled out or have long term injuries
- Players who have injuries whose status is questionable, pending more information
- Players returning from injury
- Training ground reports from the last {lookback_days} days

Search timeframe: Last {lookback_days} days (from {search_from} to today)
Today's date: {datetime.now().strftime("%B %d, %Y")}

Make sure to include any existing injuries that are still ongoing as well as any new injury news.

Return your findings in the JSON format specified in the system instructions.
"""
        
        return {
            "role": "user",
            "content": prompt
        }
    
    def _build_system_message(self) -> Dict[str, Any]: 
        """
        Build system message for the Grok API.
        """

        prompt = """
You are a sports injury research assistant for the 2025/2026 football season.

Your task: Search the web in real-time for injury news about specific players before upcoming fixtures.

What to search for:
- Injury updates and recovery status
- Training/practice participation
- Manager or medical staff comments
- Match availability and fitness concerns
- Recent performance if returning from injury

Search sources: Team websites, news outlets, X (Twitter), sports forums, official announcements.

Requirements:
- Prioritize information from the last 48 hours
= Always use full names of players, not nicknames or abbreviations
- Include source URLs for all information
- Prioritize confirmed information from official sources
- Include relevant speculation or rumours, but note them as such in the description
- If no recent news exists, state that explicitly

Return your findings in the following JSON format:
{
    "description": "1-2 paragraphs summarizing all news and speculation",
    "confirmed_out": [
        {
            "player_name": "Player Name", 
            "injury": "Reason for being out",
            "status": "Status of the player",
            "details": "Details of the injury",
            "sources": ["Source 1", "Source 2", "Source 3"]
        }
    ],
    "questionable": [
        {
            "player_name": "Player Name", 
            "injury": "Reason for being questionable",
            "status": "Status of the player",
            "details": "Details of the injury",
            "sources": ["Source 1", "Source 2", "Source 3"]
        }
    ],
    "returned_to_training": [
        {
            "player_name": "Player Name", 
            "injury": "Previous injury",
            "status": "Status of the player",
            "details": "Details of recovery",
            "sources": ["Source 1", "Source 2", "Source 3"]
        }
    ],
    "manager_comments": [
        {
            "source": "Source of comment",
            "comment": "Manager's comments here"
        }
    ],
    "speculation": [
        {
            "source": "Source of speculation",
            "speculation": "Speculation here"
        }
    ]
}

"""
        return {
            "role": "system",
            "content": prompt
        }
    
def test_agent():
    """Quick test function."""
    from dotenv import load_dotenv
    load_dotenv()
    
    # Initialize clients
    grok_client = GrokClient()
    agent = ResearchAgent(grok_client)
    
    # Test with a well-known player
    context = TeamContext(
        team="Oxford United",
        fixture="Oxford United vs Ipswich Town",
        fixture_date=datetime(2025, 11, 28, 19, 45)
    )
    
    findings = agent.research_team(context)
    
    print("\n" + "="*60)
    print("📊 Research Results")
    print("="*60)
    print(f"Team: {findings.team_name}")
    print(f"Sources found: {len(findings.sources)}")
    print(f"Confidence: {findings.confidence_score}")
    print(f"\nKey Findings:")
    for i, finding in enumerate(findings.findings, 1):
        print(f"{i}. {finding}")
    print(f"\nSources:")
    for i, source in enumerate(findings.sources, 1):
        print(f"{i}. {source.title}")
        print(f"       URL: {source.url}")


if __name__ == "__main__":
    test_agent()

