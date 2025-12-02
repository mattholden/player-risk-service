from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import json

from src.clients.grok_client import GrokClient
from src.agents.models import Source, InjuryResearchFindings, TeamContext, TeamAnalysis, PlayerRisk

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

    def analyze_player_risk(
        self, 
        context: TeamContext,
        injury_news: List[str],
        expert_analysis: str) -> PlayerRisk:
        """
        Analyze the risk of a player playing in a fixture.
        """
        print(f"\n🔍 Analyzing Risk for {context.team}")
        print(f"   Fixture: {context.fixture}")
        print(f"   Date: {context.fixture_date.strftime('%B %d, %Y')}")
        print(f"   Team: {context.team}")
        print(f"   Opponent: {context.opponent}")

        user_message = self._build_user_message(context, injury_news, expert_analysis)
        system_message = self._build_system_message()
        messages = [system_message, user_message]
        response = self.grok_client.chat_completion(messages=messages)
        content = response.get('content', '')
        print("Content:")
        print(content)
        return None # TODO: Implement parsing of response

    def _build_user_message(self, context: TeamContext, injury_news: List[str], expert_analysis: str) -> Dict[str, Any]:
        
        # Format injury news
        injury_summary = "\n".join([f"- {item}" for item in injury_news]) if injury_news else "- No significant injuries reported"
        
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

Consider:
1. **Direct impacts** - Injured players with active prop lines (especially if ruled out)
2. **Replacement starters** - Players gaining significant opportunity
3. **Usage beneficiaries** - Players likely to see increased targets/touches/minutes
4. **Matchup advantages** - Players facing weakened opposition
5. **Returning players** - Usage uncertainty creating mispriced lines

**Quality filters:**
- Must be a meaningful edge (not just "might get 2 more minutes")
- Impact should be quantifiable (usage, matchups, role changes)
- Focus on players likely to have active prop markets
- Exclude speculative or marginal impacts

Return a JSON array of opportunities with alert levels. Be ruthless - only return players where you'd genuinely look for an edge.

If no strong opportunities exist, return an empty array: []
"""
        return {"role": "user", "content": prompt}

    def _build_system_message(self) -> Dict[str, Any]:
        prompt = """
You are a sharp sports bettor ("shark") who specializes in identifying player prop betting edges from injury news.

Your expertise: Finding market inefficiencies when sportsbooks fail to properly adjust player lines based on injury reports and tactical changes.

**Alert Level Framework:**

HIGH ALERT - Near-certain opportunity:
- Player ruled OUT (guaranteed under on all props if lines exist)
- Player confirmed as replacement starter (massive usage spike expected)
- Clear role change with quantifiable impact

MEDIUM ALERT - Strong edge potential:
- Player questionable/doubtful (uncertainty = potential mispricing)
- Player returning from injury (minutes/usage uncertainty)
- Significant role expansion due to teammate's absence
- Opponent missing key defender matched up against this player

LOW ALERT - Worth monitoring:
- Minor role changes
- Indirect impact from injuries
- Situational advantages that may not move lines enough

**Key Principles:**
- Only identify players where injury news creates meaningful information asymmetry
- Focus on situations where prop lines likely don't reflect new reality
- Consider both direct impacts (injured players) and indirect (beneficiaries)
- Be selective - return only actionable opportunities, not every affected player
- One sentence explanations must be specific and actionable

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

    def _parse_response(self, content: str) -> List[PlayerRisk]:
        """
        Parse the response into a list of PlayerRisk objects.
        """
        return json.loads(content)