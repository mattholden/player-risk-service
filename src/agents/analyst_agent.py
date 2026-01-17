from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json
import re

from src.clients.grok_client import GrokClient
from src.agents.models import TeamContext, Source, TeamAnalysis
from src.logging import get_logger
from prompts.base import AgentPrompt
from src.utils.strict_prompting import strict_format
class AnalystAgent:
    """
    Agent that analyzes injury news and determines the impact on a team's performance.
    """
    def __init__(self, grok_client: GrokClient, prompts: AgentPrompt):
        """
        Initialize Analyst Agent.
        
        Args:
            grok_client: Initialized GrokClient instance
            prompts: AgentPrompt instance
        """
        self.grok_client = grok_client
        self.prompts = prompts
        self.logger = get_logger()
        self.logger.success("Analyst Agent Initialized")

    def analyze_injury_news(
        self,
        context: TeamContext, 
        injury_news: str
        ) -> TeamAnalysis:
        """
        Analyze injury news and determine the impact on a team's performance.
        """

        # Build the search prompt
        # user_message = self._build_user_message(injury_news, context)
        # self.logger.agent_user_message("Analyst Agent", user_message)
        # system_message = self._build_system_message()
        # self.logger.agent_system_message("Analyst Agent", system_message)

        ###### Building prompts from prompt registry
        ###### *****If truly making it sport agnostic then parameters have to be extracted specifically based on the soccer user template
        user_message = self.prompts.generate_user_prompt(
            context=context, 
            injury_news=injury_news
        )
        
        system_message = self.prompts.generate_system_prompt()
        
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

CRITICAL: Use ONLY 2025/2026 season data. Before analyzing replacements, verify current squad rosters as of {current_date}.

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
1. **FIRST**: Search "{context.team} official squad December 2025" OR "{context.team}.com/squad" to verify current roster
2. **SECOND**: Search "{context.opponent} official squad December 2025" OR "{context.opponent}.com/squad" to verify current roster  
3. Review recent match reports from last 2-4 weeks to see who actually played
4. Check Transfermarkt for any recent transfers (November-December 2025)
5. Current season statistics and form

**CRITICAL**: If you mention a replacement player, search "[PLAYER NAME] [TEAM] 2025" to confirm they're currently with the club.
Do NOT assume players from 2024/25 season are still with the team.

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
In addition to your expertise on the game of football, searching for recent news reports and updates about the team are crutial for analyzing how a team will approach their next fixture.
You have access to web search and X search tools which help you stay up to date with the latest news and information about a particular team.


**IMPORTANT: Current Season Context**
We are in the 2025/2026 football season. When researching:
- ONLY use current season (2025/2026) squad rosters and statistics
- Verify information is from 2025 or later
- Prioritize official sources for squad lists (see below)
- Disregard data from previous seasons unless comparing historical context
- If you find conflicting roster information, note the discrepancy

**Trusted Squad Roster Sources (in priority order):**
1. Official club websites (e.g., arsenal.com/first-team, brentfordfc.com/players)
2. Trusted Soccerway website: https://us.soccerway.com/
3. Transfermarkt.com (most up-to-date transfer database)
4. BBC Sport squad pages
5. Sky Sports squad lists

**What to verify:**
- Player still with the club (check for recent transfers OUT)
- New signings in current window (check for transfers IN)
- Loan status (loaned out vs loaned in)
- If a player is mentioned but you can't verify they're in the current squad, FLAG IT

Your role: Assess how player injuries impact team strategy, lineups, and match dynamics.

Analysis framework:
1. Player importance - Current season role, minutes played, key statistics
2. Depth assessment - Available replacements IN CURRENT SQUAD and quality drop-off
3. Tactical impact - How absence changes team shape/strategy this season
4. Opposition response - How opponents might exploit weaknesses
5. Returning players - Impact of players coming back from injury

Research priorities when using web search:
- Search: "TEAM_NAME official squad 2025/2026" OR "TEAM_NAME current squad December 2025"
- Search: "PLAYER_NAME TEAM_NAME transfer 2025" (if uncertain about roster status)
- Recent match reports (last 4-6 weeks) for confirmed lineups
- Official club announcements

Output requirements:
- Write a concise analytical report (1-2 paragraphs)
- Always use full names of players, not nicknames or abbreviations
- Focus on tactical and strategic implications, not speculation
- Highlight specific players who may benefit or face challenges
- If you mention a replacement player, CONFIRM they are in the current squad
- Flag any uncertainty: "Note: Could not verify [Player X] is still with the club as of December 2025"
- Note confidence level based on information quality

You have access to real-time web search to research team tactics, player stats, and recent form.
"""
        return {
            "role": "system", 
            "content": prompt
        }