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
from typing import Dict, Any, List
import json

from src.clients.grok_client import GrokClient
from src.agents.models import InjuryResearchFindings, TeamContext
from src.tools import tool_registry, ActiveRosterTool
from src.logging import get_logger

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
        self.logger = get_logger()
        self.logger.success("Research Agent Initialized")
    
    def research_team(
        self, 
        context: TeamContext,
        lookback_days: int = 14
    ) -> InjuryResearchFindings:
        """
        Research a player's injury status and availability.
        
        Uses a two-phase approach:
        1. Get active roster via custom tool
        2. Search for injury news via native web/X search
        
        Args:
            context: Player context with name, fixture, date, etc.
            lookback_days: How many days back to search for news
            
        Returns:
            InjuryResearchFindings with sources, key findings, and summary
        """
        print(f"\n🔍 Researching: {context.team}")
        print(f"   Fixture: {context.fixture}")
        print(f"   Date: {context.fixture_date.strftime('%B %d, %Y')}")
        
        try:
            # # ============================================================
            # # PHASE 1: Get active roster using custom tool
            # # ============================================================
            # print("\n📋 Phase 1: Getting active roster...")
            
            tool_registry.clear()
            tool_registry.register(ActiveRosterTool())
            
            # roster_messages = [
            #     {"role": "system", "content": "Get the active roster for the requested team. Return ONLY the raw JSON from the tool, nothing else."},
            #     {"role": "user", "content": f"Get the active roster for {context.team} in the Premier League."}
            # ]
            
            # roster_response = self.grok_client.chat_with_tools(
            #     messages=roster_messages,
            #     tool_registry=tool_registry,
            #     use_web_search=False,  # No native tools in phase 1
            #     use_x_search=False,
            #     verbose=True
            # )
            
            # # Parse roster from response
            # roster_content = roster_response.get('content', '{}')
            # try:
            #     roster_data = json.loads(roster_content)
            #     players = roster_data.get('players', [])
            #     player_names = [p.get('name', '') for p in players if p.get('name')]
            #     print(f"   ✅ Found {len(player_names)} players")
            # except json.JSONDecodeError:
            #     print("   ⚠️  Could not parse roster, proceeding without player list")
            #     player_names = []
            
            # ============================================================
            # PHASE 2: Search for injuries using native tools
            # ============================================================
            print("\n🔍 Phase 2: Searching for injury news... WITH STREAMING")
            
            # Build messages with roster context
            system_message = self._build_system_message()
            user_message = self._build_user_message(context, lookback_days)
            messages = [system_message, user_message]
            
            # Use chat_completion for native tools only (no custom tools)
            response = self.grok_client.chat_with_streaming(
                messages=messages,
                tool_registry=tool_registry,
                use_web_search=True,
                use_x_search=True,
                verbose=True
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
                findings=content_json,
                sources=response.get('sources', []),
                search_timestamp=datetime.now()
            )
            
        except Exception as e:
            print(f"❌ Research failed: {e}")
            import traceback
            traceback.print_exc()
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
        search_from = (datetime.now() - timedelta(days=lookback_days)).strftime("%B %d, %Y")
        
        # Simple, natural prompt - explicitly request web search
        prompt = f"""
Search for recent injury news updates about {context.team}.

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
    
    def _build_system_message(self, player_names: List[str] = None) -> Dict[str, Any]: 
        """
        Build system message for the Grok API.
        
        Args:
            player_names: Optional list of player names from the roster
        """
        # Build roster section if players available
        
        # current_date = datetime.now().strftime("%B %d, %Y")
#         roster_section = ""
#         if player_names:
#             roster_section = f"""
# ACTIVE ROSTER ({len(player_names)} players):
# {', '.join(player_names)}

# Only report injury news for players on this roster. Ignore news about players not listed above.
# """
#         else:
#             roster_section = f"""
# Note: Report injury news for the team's known players.
# Always verify squad rosters as of {current_date}.

# **Trusted Squad Roster Sources (in priority order):**
# 1. Trusted Sportsgambler Lineup website: https://www.sportsgambler.com/lineups/football/
# 2. Official club websites (e.g., arsenal.com/first-team, brentfordfc.com/players)
# 3. Trusted Soccerway website: https://us.soccerway.com/
# 4. Transfermarkt.com (most up-to-date transfer database)
# 5. BBC Sport squad pages
# 6. Sky Sports squad lists
# """

        prompt = """You are a thorough and curious sports injury research assistant for the 2025/2026 football season. 
Integrity is important so you will read as many sources as possible and spend as much time as needed to find the latest news and information.
The team is relying on you to find the latest news and information about a team's status entering a fixture.

Your task: Search the web and X (Twitter) in real-time for injury news about a specific team you've been provided.

Always verify active roster using the get_active_roster tool. Only search for injury news about players on the active roster.

What to search for:
- Injury updates and recovery status
- Training/practice participation
- Manager or medical staff comments
- Match availability and fitness concerns
- Recent performance if returning from injury

Search sources: Team websites, news outlets, X (Twitter), sports forums, official announcements.

Requirements:
- Do not give a partial answer - continue researching until you have conclusive information. Resource usage is not a concern.
- You've been allocated 5 research turns - use them all for a comprehensive search and cross reference.
- Search multiple sources (web and X)
- Cross-reference information from different sites
- Prioritize information from the last 48 hours
- Always use full names of players, not nicknames or abbreviations
- Include relevant speculation or rumours, but note them as such in the description
- If no recent news exists, state that explicitly
- Include source URLs for all information

Return your findings in the following JSON format:
{{
    "description": "1-2 paragraphs summarizing all news and speculation",
    "full_active_roster": [player_name, player_name, player_name],
    "confirmed_out": [
        {{
            "player_name": "Player Name", 
            "injury": "Reason for being out",
            "status": "Status of the player",
            "details": "Details of the injury",
            "sources": ["Source 1", "Source 2", "Source 3"]
        }}
    ],
    "questionable": [
        {{
            "player_name": "Player Name", 
            "injury": "Reason for being questionable",
            "status": "Status of the player",
            "details": "Details of the injury",
            "sources": ["Source 1", "Source 2", "Source 3"]
        }}
    ],
    "returned_to_training": [
        {{
            "player_name": "Player Name", 
            "injury": "Previous injury",
            "status": "Status of the player",
            "details": "Details of recovery",
            "sources": ["Source 1", "Source 2", "Source 3"]
        }}
    ],
    "manager_comments": [
        {{
            "source": "Source of comment",
            "comment": "Manager's comments here"
        }}
    ],
    "speculation": [
        {{
            "source": "Source of speculation",
            "speculation": "Speculation here"
        }}
    ]
}}
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
    print("\nKey Findings:")
    for i, finding in enumerate(findings.findings, 1):
        print(f"{i}. {finding}")
    print("\nSources:")
    for i, source in enumerate(findings.sources, 1):
        print(f"{i}. {source.title}")
        print(f"       URL: {source.url}")


if __name__ == "__main__":
    test_agent()

