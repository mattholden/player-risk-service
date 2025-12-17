from datetime import datetime
from typing import Dict, Any, List
import json

from src.clients.grok_client import GrokClient
from src.agents.models import TeamContext, PlayerAlert
from database.enums import AlertLevel

class SharkAgent:
    """
    Agent that uses the Shark API to get the latest news and information about a team.
    """
    def __init__(self, grok_client: GrokClient):
        """
        Initialize Shark Agent.
        """
        self.grok_client = grok_client
        print("✅ Shark Agent initialized")

    def analyze_player_risk_for_fixture(
        self,
        team_analyses: List[Dict[str, Any]]) -> List[PlayerAlert]:
        """
        Analyze player risk for an entire fixture (both teams).
        
        This prevents duplicate alerts by processing both teams' data together.
        
        Args:
            team_analyses: List of dicts containing:
                - context: TeamContext
                - research: Research findings
                - analyst: Analyst tactical analysis
                
        Returns:
            List of PlayerAlert objects (no duplicates)
        """
        if not team_analyses:
            return []
        
        # Extract fixture info from first context
        fixture = team_analyses[0]['context'].fixture
        fixture_date = team_analyses[0]['context'].fixture_date
        
        print(f"\n🦈 Analyzing Fixture Risk: {fixture}")
        print(f"   Date: {fixture_date.strftime('%B %d, %Y')}")
        print(f"   Processing {len(team_analyses)} teams together (prevents duplicates)")
        
        user_message = self._build_fixture_user_message(team_analyses)
        system_message = self._build_system_message()
        messages = [system_message, user_message]
        
        response = self.grok_client.chat_completion(
            messages=messages,
            use_web_search=True,
            use_x_search=True,
            return_citations=True,
        )
        content = response.get('content', '')
        print("\n" + "="*70)
        print("🔍 DEBUG: Raw Shark Response")
        print("="*70)
        print(content)
        print("="*70 + "\n")
        
        # Parse the response using the first context for fixture info
        return self._parse_response(content, team_analyses[0]['context'])
    
    def analyze_player_risk(
        self, 
        context: TeamContext,
        injury_news: List[str],
        expert_analysis: str) -> List[PlayerAlert]:
        """
        Analyze the risk of a player playing in a fixture (single team).
        
        DEPRECATED: Use analyze_player_risk_for_fixture() instead to prevent duplicates.
        This method is kept for backward compatibility.
        
        Returns:
            List of PlayerAlert objects with alert levels and descriptions
        """
        print(f"\n🔍 Analyzing Risk for {context.team}")
        print(f"   Fixture: {context.fixture}")
        print(f"   Date: {context.fixture_date.strftime('%B %d, %Y')}")
        print(f"   Team: {context.team}")
        print(f"   Opponent: {context.opponent}")

        user_message = self._build_user_message(context, injury_news, expert_analysis)
        system_message = self._build_system_message()
        messages = [system_message, user_message]
        response = self.grok_client.chat_completion(
            messages=messages,
            use_web_search=True,
            use_x_search=True,
            return_citations=True,
        )
        content = response.get('content', '')
        print("\n" + "="*70)
        print("🔍 DEBUG: Raw Shark Response")
        print("="*70)
        print(content)
        print("="*70 + "\n")
        
        # Parse the response into PlayerAlert objects
        return self._parse_response(content, context)

    def _build_fixture_user_message(self, team_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build user message for fixture-level analysis (both teams combined).
        
        This prevents duplicate alerts by giving the agent all fixture information at once.
        """
        fixture = team_analyses[0]['context'].fixture
        fixture_date = team_analyses[0]['context'].fixture_date
        current_date = datetime.now().strftime("%B %d, %Y")
        
        # Build combined injury reports and analyses
        team_sections = []
        for analysis in team_analyses:
            context = analysis['context']
            research = analysis['research']
            analyst = analysis['analyst']
            
            # Format injury news
            injury_summary = "\n".join([f"  - {item}" for item in research]) if isinstance(research, list) else f"  - {research}"
            
            team_section = f"""
**{context.team}** (vs {context.opponent}):

Injury Report:
{injury_summary}

Expert Tactical Analysis:
{analyst}
"""
            team_sections.append(team_section)
        
        combined_teams = "\n" + "="*70 + "\n".join(team_sections)
        
        prompt = f"""
Identify player prop betting opportunities from injury news for this fixture.

**Match Details:**
- Fixture: {fixture}
- Date: {fixture_date.strftime("%B %d, %Y")}

**FIXTURE-WIDE INJURY & TACTICAL ANALYSIS:**
{combined_teams}

**Your Task:**
Analyze the injury situation and expert analysis from BOTH teams to identify players with potential betting line edges.

**CRITICAL - Avoid Duplicate Alerts:**
- You are seeing data from BOTH teams in this fixture
- Generate ONLY ONE alert per player (don't repeat a player just because they appear in both teams' analyses)
- If a player is mentioned in both teams' contexts, combine the reasoning into one comprehensive alert

**BEFORE adding any player to alerts:**
1. If the analyst mentions a replacement player you're unfamiliar with, search verify their roster status as of {current_date}
2. Verify they're currently with the team (not transferred out as of {current_date})

**Trusted Squad Roster Sources (in priority order):**
1. Official club websites (e.g., arsenal.com/first-team, brentfordfc.com/players)
2. Trusted Soccerway website: https://us.soccerway.com/
3. Transfermarkt.com (most up-to-date transfer database)
4. BBC Sport squad pages
5. Sky Sports squad lists

Consider:
1. **Direct impacts** - Injured players with active prop lines (especially if ruled out)
2. **Replacement starters** - Players gaining significant opportunity (VERIFY THEY'RE STILL WITH THE TEAM)
3. **Usage beneficiaries** - Players likely to see increased targets/touches/minutes
4. **Matchup advantages** - Players facing weakened opposition
5. **Returning players** - Usage uncertainty creating mispriced lines
6. **Cross-team impacts** - How one team's injuries create opportunities for the opponent

**Quality filters:**
- Must be a meaningful edge (not just "might get 2 more minutes")
- Impact should be quantifiable (usage, matchups, role changes)
- Exclude speculative or marginal impacts

Return a JSON array of opportunities with alert levels. 
Only return players where you'd genuinely look for an edge or want to keep on watch for more information to be released closer to the fixture.

If no strong opportunities exist, return an empty array: []
"""
        return {"role": "user", "content": prompt}
    
    def _build_user_message(self, context: TeamContext, injury_news: str, expert_analysis: str) -> Dict[str, Any]:
        
        # Format injury news
        injury_summary = "\n".join([f"- {item}" for item in injury_news]) if injury_news else "- No significant injuries reported"
        current_date = datetime.now().strftime("%B %d, %Y")
        prompt = f"""
Identify player prop betting opportunities from injury news for this fixture.

**Match Details:**
- Fixture: {context.fixture}
- Date: {context.fixture_date.strftime("%B %d, %Y")}
- Team: {context.team}
- Opponent: {context.opponent}

**Injury Report:**
{injury_summary}

**Expert Tactical Analysis:**
{expert_analysis}

**Your Task:**
Analyze the injury situation and expert analysis to identify players with potential betting line edges.

**BEFORE adding any player to alerts:**
1. If the analyst mentions a replacement player you're unfamiliar with, search verify their roster status as of {current_date}"
2. Verify they're currently with the team (not transferred out as of {current_date})

**Trusted Squad Roster Sources (in priority order):**
1. Official club websites (e.g., arsenal.com/first-team, brentfordfc.com/players)
2. Trusted Soccerway website: https://us.soccerway.com/
3. Transfermarkt.com (most up-to-date transfer database)
4. BBC Sport squad pages
5. Sky Sports squad lists

Consider:
1. **Direct impacts** - Injured players with active prop lines (especially if ruled out)
2. **Replacement starters** - Players gaining significant opportunity (VERIFY THEY'RE STILL WITH THE TEAM)
3. **Usage beneficiaries** - Players likely to see increased targets/touches/minutes
4. **Matchup advantages** - Players facing weakened opposition
5. **Returning players** - Usage uncertainty creating mispriced lines

**Quality filters:**
- Must be a meaningful edge (not just "might get 2 more minutes")
- Impact should be quantifiable (usage, matchups, role changes)
- Exclude speculative or marginal impacts

Return a JSON array of opportunities with alert levels. 
Only return players where you'd genuinely look for an edge or want to keep on watch for more information to be released closer to the fixture.

If no strong opportunities exist, return an empty array: []
"""
        return {"role": "user", "content": prompt}

    def _build_system_message(self) -> Dict[str, Any]:
        prompt = """
You are a sharp sports bettor ("shark") who specializes in identifying player prop betting edges from injury news. 
Lucky for you, you have insider information. You've been provided injury information about both teams in a fixture as well as feedback from expert analysts on both teams describing the tactical implications of the injury report.

Your expertise: Finding market inefficiencies where recent injury and team news results in sportsbooks failing to properly adjust player lines.

**CRITICAL VALIDATION REQUIREMENT:**
Before including ANY player in your alerts, you MUST verify they are currently with the team. Only include players you can confirm are in the current squad

**Trusted Sources for Roster Verification:**
1. Official team websites (e.g., arsenal.com/squad, brentfordfc.com/players)
2. Transfermarkt.com (check for recent transfers)
3. Recent match lineups (last 2-4 weeks)
4. Premier League official squad lists

**Alert Level Framework:**

HIGH ALERT - Near-certain opportunity:
- Player recently ruled OUT or has been newly diagnosed with a long term injury
- Player recently confirmed as a replacement starter (massive usage spike expected)
- Clear recent role change with quantifiable impact
- ONLY if you can verify the replacement player is currently with the team

MEDIUM ALERT - Strong edge potential:
- Player injury status is questionable (there is injury concern, but uncertainty about whether they will be available for the fixture)
- Player returning from injury (minutes/usage uncertainty)
- Significant role expansion due to teammate's absence
- Opponent missing key defender matched up against this player
- ONLY if player roster status is confirmed

LOW ALERT - Worth monitoring:
- Replacement player for an injury that occured more than 2 weeks ago.
- Minor injuries that are likely to be resolved in time for the fixture
- Indirect impact from injuries
- Situational advantages that may not move lines enough

**Key Principles:**
- **NO DUPLICATE ALERTS**: Generate only ONE alert per player, even if they're mentioned in multiple team analyses
- Players that have been ruled out for more than 2 weeks have very low level alerts as the markets have most likely already adjusted to the news.
- Only identify players where recent injury news creates meaningful information asymmetry
- Focus on situations where prop lines likely don't reflect new reality
- Consider both direct impacts (injured players) and indirect (beneficiaries)
- Always use full names of players, not nicknames or abbreviations
- Be selective - return only actionable opportunities, not every affected player
- One sentence explanations must be specific and actionable
- If a player appears in analyses for both teams, consolidate into ONE comprehensive alert

**Output Format:**
Return ONLY a JSON array of player opportunities:
[
  {
    "player_name": "Full Name",
    "alert_level": "high|medium|low",
    "reasoning": "One specific sentence explaining the edge opportunity"
  }
]

Do not include players with no edge potential. Empty array if no opportunities exist.
"""
        return {
            "role": "system", 
            "content": prompt
        }

    def _parse_response(self, content: str, context: TeamContext) -> List[PlayerAlert]:
        """
        Parse the JSON response into a list of PlayerAlert objects.
        
        Args:
            content: JSON string from Grok containing player alerts
            
        Returns:
            List of PlayerAlert objects with proper enum values
        """
        try:
            # Parse the JSON string
            data = json.loads(content)
            
            # If it's not a list, wrap it
            if not isinstance(data, list):
                data = [data]
            
            # Convert each dict to a PlayerAlert object
            alerts = []
            for item in data:
                # Map the string alert_level to AlertLevel enum
                alert_level_str = item.get('alert_level', 'low').lower()
                
                # Convert string to AlertLevel enum
                alert_level_map = {
                    'high': AlertLevel.HIGH_ALERT,
                    'medium': AlertLevel.MEDIUM_ALERT,
                    'low': AlertLevel.LOW_ALERT,
                    'no_alert': AlertLevel.NO_ALERT,
                }
                alert_level = alert_level_map.get(alert_level_str, AlertLevel.LOW_ALERT)
                
                # Create PlayerAlert object (map 'reasoning' to 'description')
                alert = PlayerAlert(
                    player_name=item.get('player_name', ''),
                    fixture=context.fixture,
                    fixture_date=context.fixture_date,
                    alert_level=alert_level,
                    description=item.get('reasoning', item.get('description', ''))
                )
                alerts.append(alert)
            
            print(f"\n✅ Parsed {len(alerts)} player alerts")
            return alerts
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON response: {e}")
            print(f"   Content: {content[:200]}...")
            return []
        except Exception as e:
            print(f"❌ Error parsing response: {e}")
            return []