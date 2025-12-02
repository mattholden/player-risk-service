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
            )
            
            # DEBUG: Print raw response to see what Grok returned
            print("\n" + "="*70)
            print("🔍 DEBUG: Raw Grok Response")
            print("="*70)
            print(response.get('content', ''))  # First 1000 chars
            print("="*70 + "\n")
            
            # Parse the response into structured findings
            findings = self._parse_response(response, context)
            
            return findings
            
        except Exception as e:
            print(f"❌ Research failed: {e}")
            # Return empty findings on error
            return InjuryResearchFindings(
                team_name=context.team,
                fixture=context.fixture,
                findings=[],
                sources=[],
                confidence_score=0.0,
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
- Players ruled out or doubtful
- Players returning from injury
- Players who have had persistent injuries
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
- Include source URLs for all information
- Be objective - report only confirmed information, note speculation clearly
- If no recent news exists, state that explicitly

Return findings as structured JSON:
{
  "summaries": ["Concise finding 1", "Concise finding 2"],
  "sources": [{"number": 1, "title": "Article title", "url": "https://...", "date": "YYYY-MM-DD"}]
}
"""
        return {
            "role": "system",
            "content": prompt
        }
    
    def _parse_response(
        self, 
        response: dict, 
        context: TeamContext
    ) -> InjuryResearchFindings:
        """
        Parse Grok's response into structured ResearchFindings.
        
        Args:
            response: Raw response from Grok API
            context: Original player context
            
        Returns:
            Structured ResearchFindings object
        """
        content = response.get('content', '')
        
        # Try to extract JSON from the response
        try:
            # Grok might wrap JSON in markdown code blocks
            if '```json' in content:
                json_start = content.find('```json') + 7
                json_end = content.find('```', json_start)
                json_str = content[json_start:json_end].strip()
                print("First Condition")
            elif '```' in content:
                json_start = content.find('```') + 3
                json_end = content.find('```', json_start)
                json_str = content[json_start:json_end].strip()
                print("Second Condition")
            elif '{' in content and '}' in content:
                # Try to extract raw JSON
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                json_str = content[json_start:json_end]
                print("Third Condition")
            else:
                # No JSON found, create findings from raw text
                print("Fourth Condition")
                return self._create_findings_from_text(content, context)
            
            # Parse the JSON
            data = json.loads(json_str)
            
            # Extract sources
            sources = []
            for src in data.get('sources', []):
                try:
                    sources.append(Source(
                        url=src.get('url', ''),
                        title=src.get('title', ''),
                    ))
                except Exception as e:
                    print(f"⚠️  Could not parse source: {e}")
                    continue
            
            # Create findings
            return InjuryResearchFindings(
                team_name=context.team,
                fixture=context.fixture,
                findings=data.get('summaries', []),
                sources=data.get('sources', []),
                confidence_score=data.get('confidence_score', 0.0),
                search_timestamp=datetime.now()
            )
            
        except Exception as e:
            print(f"⚠️  JSON parsing failed: {e}")
            print("   Falling back to text-based extraction")
            return self._create_findings_from_text(content, context)
    
    def _create_findings_from_text(
        self, 
        content: str, 
        context: TeamContext
    ) -> InjuryResearchFindings:
        """
        Create findings from unstructured text when JSON parsing fails.
        
        Args:
            content: Raw text content from Grok
            context: Player context
            
        Returns:
            Basic InjuryResearchFindings extracted from text
        """
        # Try to extract URLs from text
        import re
        urls = re.findall(r'https?://[^\s\)]+', content)
        
        # Create basic sources from URLs
        sources = []
        for url in urls[:10]:  # Limit to 10 sources
            sources.append(Source(
                url=url,
                title="Source found in research",
            ))
        
        # Use first 300 chars as summary
        summary = content[:300] + "..." if len(content) > 300 else content
        
        # Try to extract key points (sentences with player name)
        key_findings = []
        sentences = content.split('.')
        for sentence in sentences:  # Limit to 5 key findings
            if context.name.split()[0] in sentence:  # Check for player's first name
                key_findings.append(sentence.strip() + '.')
        
        return InjuryResearchFindings(
            team_name=context.team,
            fixture=context.fixture,
            findings=key_findings if key_findings else ["Research completed but no structured findings available"],
            sources=sources,
            confidence_score=0.3,  # Low confidence for unstructured data
            search_timestamp=datetime.now()
        )
    
    def _parse_datetime(self, dt_string: Optional[str]) -> Optional[datetime]:
        """
        Parse datetime string with fallback handling.
        
        Args:
            dt_string: Datetime string in various formats
            
        Returns:
            Datetime object or None
        """
        if not dt_string:
            return None
        
        try:
            # Try ISO format first
            return datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        except:
            try:
                # Try common formats
                from dateutil import parser
                return parser.parse(dt_string)
            except:
                return None


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

