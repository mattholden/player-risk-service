from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json
import re

from src.clients.grok_client import GrokClient
from src.agents.models import TeamContext, Source, TeamAnalysis


class AnalystAgent:
    """
    Agent that analyzes injury news and determines the impact on a team's performance.
    """
    def __init__(self, grok_client: GrokClient):
        """
        Initialize Analyst Agent.
        
        Args:
            grok_client: Initialized GrokClient instance
        """
        self.grok_client = grok_client
        print("✅ Analyst Agent initialized")

    def analyze_injury_news(
        self,
        context: TeamContext, 
        injury_news: str
        ) -> TeamAnalysis:
        """
        Analyze injury news and determine the impact on a team's performance.
        """
        print(f"\n🔍 Anaylzing Fixture: {context.fixture}")
        print(f"   Fixture: {context.fixture}")
        print(f"   Date: {context.fixture_date.strftime('%B %d, %Y')}")
        print(f"   Team: {context.team}")
        print(f"   Opponent: {context.opponent}")

        # Build the search prompt
        user_message = self._build_user_message(injury_news, context)
        system_message = self._build_system_message()
        print("System message:")
        print(system_message)
        print("User message:")
        print(user_message)
        messages = [system_message, user_message]

        try:
            response = self.grok_client.chat_completion(
                messages=messages,
                use_web_search=True,
                use_x_search=True,
                return_citations=True,
            )
            print("\n" + "="*70)
            print("🔍 DEBUG: Raw Grok Response")
            print("="*70)
            print(response.get('content', ''))
            print("="*70 + "\n")
        except Exception as e:
            print(f"❌ Analysis failed: {e}")
            return None
        
        return TeamAnalysis(
            team_name=context.team,
            opponent_name=context.opponent,
            fixture=context.fixture,
            team_analysis=self.clean_response(response.get('content', ''))
        )
    
    def clean_response(self, text: str) -> str:
        # Remove markdown formatting
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Remove **bold**
        text = re.sub(r'###\s+', '', text)  # Remove ### headers
        return text


    def _build_user_message(self, injury_news: str, context: TeamContext) -> Dict[str, Any]:
        
        # Format injury news clearly
        current_date = datetime.now().strftime("%B %d, %Y")
        
        prompt = f"""
Analyze the tactical implications of reported injuries for this upcoming fixture. 
Based on the severity of any injuries, determine if the team is likely to make any adjustments to their game strategy.

**Match Details:**
- Fixture: {context.fixture}
- Date: {context.fixture_date.strftime("%B %d, %Y")}
- Team: {context.team}
- Opponent: {context.opponent}
- Current Date: {current_date}
- Season: 2025/2026

**Injury Report:**
{injury_news}

**Analysis Required:**

CRITICAL: Use ONLY 2025/2026 season data. Before analyzing replacements, verify current squad rosters.

For {context.team}:
- Which positions are affected?
- If there are any serious injuries, who are the likely replacements FROM THE CURRENT SQUAD?
- Are there minor injuries that are likely to be resolved in time for the fixture?
- How might the coaches strategy change based on recent 2025/2026 matches?
- Which players gain increased opportunity?

For {context.opponent}:
- If absences are expected, how can they exploit these absences?
- What is the likelihood of any adjustments for any minor injuries?
- What adjustments might they make to their game strategy based on their current season form?
- Which opposition players become more important?

Required research:
1. Search for "{context.team} 2025/2026 squad" to verify most recent current roster
2. Search for "{context.opponent} 2025/2026 squad" to verify most recent current roster
3. Review recent match reports from the last month
4. Check current season statistics and form

Provide a comprehensive 1-2 paragraph report covering:
1. Key absences and their impact
2. Likely lineup/tactical adjustments for both teams (based on current rosters)
3. Players to watch (beneficiaries of increased opportunity)
4. Overall match dynamic implications
5. Note any limitations if current roster information is unclear

Keep analysis grounded in reported facts and current season data.
"""
        return {
            "role": "user", 
            "content": prompt
        }

    def _build_system_message(self) -> Dict[str, Any]:
        prompt = """
You are an expert football analyst specializing in tactical adjustments and squad depth analysis.

**IMPORTANT: Current Season Context**
We are in the 2025/2026 football season. When researching:
- ONLY use current season (2025/2026) squad rosters and statistics
- Verify information is from 2025 or later
- Check official team websites for current squad lists
- Disregard data from previous seasons unless comparing historical context
- Note when information may be outdated

Your role: Assess how player injuries impact team strategy, lineups, and match dynamics.

Analysis framework:
1. Player importance - Current season role, minutes played, key statistics
2. Depth assessment - Available replacements IN CURRENT SQUAD and quality drop-off
3. Tactical impact - How absence changes team shape/strategy this season
4. Opposition response - How opponents might exploit weaknesses
5. Returning players - Impact of players coming back from injury

Research priorities when using web search:
- "2025/2026 season" + team name + "squad"
- "current roster" + team name
- Recent match reports (last 4-6 weeks)
- Official club announcements

Output requirements:
- Write a concise analytical report (1-2 paragraphs)
- Always use full names of players, not nicknames or abbreviations
- Focus on tactical and strategic implications, not speculation
- Highlight specific players who may benefit or face challenges
- Note confidence level based on information quality
- Flag any uncertainty about current squad information

You have access to real-time web search to research team tactics, player stats, and recent form.
"""
        return {
            "role": "system", 
            "content": prompt
        }