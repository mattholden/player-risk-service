"""
Research Agent - Searches for player injury news using Grok.

This agent:
1. Takes a PlayerContext (name, fixture, date, etc.)
2. Builds an intelligent search prompt
3. Uses Grok's real-time search (X/Twitter + web)
4. Extracts structured findings with source citations
5. Returns ResearchFindings for downstream processing

This is Agent #1 in the two-agent pipeline.
"""

from datetime import datetime, timedelta
from typing import Optional
import json

from src.clients.grok_client import GrokClient
from src.agents.models import PlayerContext, ResearchFindings, Source


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
    
    def research_player(
        self, 
        context: PlayerContext,
        lookback_days: int = 7
    ) -> ResearchFindings:
        """
        Research a player's injury status and availability.
        
        Args:
            context: Player context with name, fixture, date, etc.
            lookback_days: How many days back to search for news
            
        Returns:
            ResearchFindings with sources, key findings, and summary
        """
        print(f"\n🔍 Researching: {context.name}")
        print(f"   Fixture: {context.fixture}")
        print(f"   Date: {context.fixture_date.strftime('%B %d, %Y')}")
        
        # Build the search prompt
        prompt = self._build_prompt(context, lookback_days)
        
        # Execute search via Grok
        try:
            response = self.grok_client.search_and_summarize(
                query=prompt,
            )
            
            # DEBUG: Print raw response to see what Grok returned
            print("\n" + "="*70)
            print("🔍 DEBUG: Raw Grok Response")
            print("="*70)
            print(response.get('content', ''))  # First 1000 chars
            print("="*70 + "\n")
            
            # Parse the response into structured findings
            findings = self._parse_response(response, context)
            
            print(f"✅ Research complete: {len(findings.sources)} sources found")
            return findings
            
        except Exception as e:
            print(f"❌ Research failed: {e}")
            # Return empty findings on error
            return ResearchFindings(
                player_name=context.name,
                sources=[],
                key_findings=[],
                summary=f"Unable to retrieve information: {str(e)}",
                confidence_score=0.0
            )
    
    def _build_prompt(self, context: PlayerContext, lookback_days: int) -> str:
        """
        Build an intelligent search prompt for Grok.
        
        Args:
            context: Player context
            lookback_days: How many days back to search
            
        Returns:
            Formatted prompt string
        """
        # Calculate the date range
        fixture_date_str = context.fixture_date.strftime("%B %d, %Y")
        search_from = (datetime.now() - timedelta(days=lookback_days)).strftime("%B %d, %Y")
        
        # Build team context if available
        team_context = f" who plays for {context.team}" if context.team else ""
        
        # Simple, natural prompt - explicitly request web search
        prompt = f"""Perform a fresh web search to find any injury news about {context.name}{team_context} for the upcoming match {context.fixture} on {fixture_date_str}.

Search the web for:
- Injury updates or concerns
- Training/practice status  
- Coach or team comments about availability
- Any fitness issues
- Recent match reports

Include all sources and URLs where you found information.
"""
        
        return prompt
    
    def _parse_response(
        self, 
        response: dict, 
        context: PlayerContext
    ) -> ResearchFindings:
        """
        Parse Grok's response into structured ResearchFindings.
        
        Args:
            response: Raw response from Grok API
            context: Original player context
            
        Returns:
            Structured ResearchFindings object
        """
        content = response.get('content', '')

        print("Content:")
        print(type(content))
        print(content)
        
        # Try to extract JSON from the response
        try:
            # Grok might wrap JSON in markdown code blocks
            if '```json' in content:
                json_start = content.find('```json') + 7
                json_end = content.find('```', json_start)
                json_str = content[json_start:json_end].strip()
            elif '```' in content:
                json_start = content.find('```') + 3
                json_end = content.find('```', json_start)
                json_str = content[json_start:json_end].strip()
            elif '{' in content and '}' in content:
                # Try to extract raw JSON
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                json_str = content[json_start:json_end]
            else:
                # No JSON found, create findings from raw text
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
            return ResearchFindings(
                player_name=context.name,
                sources=sources,
                key_findings=data.get('key_findings', []),
                summary=data.get('summary', content[:200]),
                confidence_score=data.get('confidence_score', 0.5)
            )
            
        except Exception as e:
            print(f"⚠️  JSON parsing failed: {e}")
            print("   Falling back to text-based extraction")
            return self._create_findings_from_text(content, context)
    
    def _create_findings_from_text(
        self, 
        content: str, 
        context: PlayerContext
    ) -> ResearchFindings:
        """
        Create findings from unstructured text when JSON parsing fails.
        
        Args:
            content: Raw text content from Grok
            context: Player context
            
        Returns:
            Basic ResearchFindings extracted from text
        """
        print("JSON PARSING FAILED")
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
        
        return ResearchFindings(
            player_name=context.name,
            sources=sources,
            key_findings=key_findings if key_findings else ["Research completed but no structured findings available"],
            summary=summary,
            confidence_score=0.3  # Low confidence for unstructured data
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
    context = PlayerContext(
        name="Jack Currie",
        fixture="Oxford United vs Ipswich Town",
        fixture_date=datetime(2025, 11, 28, 19, 45),
        team="Oxford United",
        position="Defender"
    )
    
    findings = agent.research_player(context)
    
    print("\n" + "="*60)
    print("📊 Research Results")
    print("="*60)
    print(f"Player: {findings.player_name}")
    print(f"Sources found: {len(findings.sources)}")
    print(f"Confidence: {findings.confidence_score}")
    print(f"\nSummary:\n{findings.summary}")
    print(f"\nKey Findings:")
    for i, finding in enumerate(findings.key_findings, 1):
        print(f"{i}. {finding}")
    print(f"\nSources:")
    for i, source in enumerate(findings.sources, 1):
        print(f"{i}. [{source.source_type}] {source.title}")
        print(f"   {source.url}")


if __name__ == "__main__":
    test_agent()

