"""
Active Roster Tool

Provides LLM agents with the ability to query active team rosters
from the database. This allows agents to know which players are
currently on a team's roster.

Uses fuzzy matching to handle variations in team/league names.
"""

import json
from typing import Dict, Any, Optional, List

from src.tools.base import BaseTool
from src.services.roster_sync import RosterSyncService
from src.utils.matching import PlayerMatcher
from database import session_scope
from database.models.roster import Roster


class ActiveRosterTool(BaseTool):
    """
    Tool for retrieving active team rosters from the database.
    
    Uses fuzzy matching to handle variations in team and league names:
    - "Liverpool" matches "Liverpool FC"
    - "Brighton" matches "Brighton & Hove Albion"
    - "Premier League" matches "English Premier League"
    
    Usage by LLM:
        When asked about a team's players, current squad, or who plays
        for a specific team, use this tool to get the roster.
    
    Returns:
        JSON with team name, league, and list of players with positions.
    """
    
    def __init__(self):
        """Initialize with roster service and matcher."""
        self.roster_service = RosterSyncService()
        self.matcher = PlayerMatcher(threshold=0.75)
    
    @property
    def name(self) -> str:
        return "get_active_roster"
    
    @property
    def description(self) -> str:
        return (
            "Get the current active roster for a sports team."
            "Returns a list of players currently on the team with their positions. "
            "Use this when you need to know who currently plays for a team."
        )
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "team": {
                    "type": "string",
                    "description": "The team name, e.g., 'Arsenal', 'Manchester United'"
                },
                "league": {
                    "type": "string",
                    "description": "The league name, e.g., 'Premier League', 'La Liga'"
                }
            },
            "required": ["team", "league"]
        }
    
    def _get_available_leagues(self) -> List[str]:
        """Get distinct league names from the database."""
        with session_scope() as session:
            leagues = session.query(Roster.league).distinct().all()
            return [league[0] for league in leagues if league[0]]
    
    def _get_teams_in_league(self, league: str) -> List[str]:
        """Get distinct team names in a specific league."""
        with session_scope() as session:
            teams = session.query(Roster.team).filter(
                Roster.league == league,
                Roster.is_active.is_(True)
            ).distinct().all()
            return [team[0] for team in teams if team[0]]
    
    def _match_league(self, input_league: str) -> Optional[str]:
        """
        Find the best matching league name from the database.
        
        Args:
            input_league: League name provided by the agent
            
        Returns:
            Matched database league name, or None if no match
        """
        available_leagues = self._get_available_leagues()
        
        if not available_leagues:
            return None
        
        # Try exact match first (case-insensitive)
        for league in available_leagues:
            if league.lower() == input_league.lower():
                return league
        
        # Try fuzzy match
        for league in available_leagues:
            if self.matcher.is_match(input_league, league):
                return league
        
        return None
    
    def _match_team(self, input_team: str, league: str) -> Optional[str]:
        """
        Find the best matching team name within a league.
        
        Args:
            input_team: Team name provided by the agent
            league: The matched league name
            
        Returns:
            Matched database team name, or None if no match
        """
        available_teams = self._get_teams_in_league(league)
        
        if not available_teams:
            return None
        
        # Try exact match first (case-insensitive)
        for team in available_teams:
            if team.lower() == input_team.lower():
                return team
        
        # Try fuzzy match
        for team in available_teams:
            if self.matcher.is_match(input_team, team):
                return team
        
        return None
    
    def execute(self, team: str, league: str) -> str:
        """
        Fetch the active roster for a team from the database.
        
        Uses fuzzy matching to find the correct team/league in the database.
        
        Args:
            team: Team name (will be fuzzy matched)
            league: League name (will be fuzzy matched)
            
        Returns:
            JSON string with roster data
        """
        try:
            # Step 1: Match the league
            matched_league = self._match_league(league)
            
            if not matched_league:
                return self._not_found_response(
                    team, league,
                    f"League '{league}' not found in database."
                )
            
            # Step 2: Match the team within that league
            matched_team = self._match_team(team, matched_league)
            
            if not matched_team:
                return self._not_found_response(
                    team, league,
                    f"Team '{team}' not found in {matched_league}."
                )
            
            # Step 3: Fetch the roster
            roster = self.roster_service.get_active_roster(matched_team, matched_league)
            
            # Format for LLM consumption
            players = [
                {
                    "name": player.get("player_name"),
                    "position": player.get("position")
                }
                for player in roster
            ]
            
            # Handle empty roster
            if not players:
                return self._not_found_response(
                    team, league,
                    f"No active players found for {matched_team} in {matched_league}."
                )
            
            return json.dumps({
                "team": team,
                "league": league,
                "player_count": len(players),
                "players": players
            })
            
        except Exception as e:
            return json.dumps({
                "error": f"Failed to fetch roster: {str(e)}",
                "team": team,
                "league": league,
                "roster_not_found": True,
                "message": "Database error occurred. Please use web search to find the current squad.",
                "suggested_sources": [
                    f"https://www.transfermarkt.com (search '{team} squad')",
                    "Official club website",
                    "https://www.premierleague.com/clubs"
                ]
            })
    
    def _not_found_response(self, team: str, league: str, reason: str) -> str:
        """
        Generate a helpful response when roster is not found.
        
        Args:
            team: Original team name searched
            league: Original league name searched
            reason: Why the roster wasn't found
            
        Returns:
            JSON string with guidance for the agent
        """
        return json.dumps({
            "team": team,
            "league": league,
            "player_count": 0,
            "players": [],
            "roster_not_found": True,
            "reason": reason,
            "message": f"No roster found in database for {team}. Please use web search to find the current squad.",
            "suggested_sources": [
                f"https://www.transfermarkt.com (search '{team} squad 2025/26')",
                "https://us.soccerway.com (comprehensive squad lists)",
                f"Official club website (search '{team} official squad')",
            ],
            "search_suggestions": [
                f'"{team},{league}" official squad 2025/26',
                f'"{team},{league}" current roster',
                f'site:transfermarkt.com "{team},{league}" squad'
            ]
        })
