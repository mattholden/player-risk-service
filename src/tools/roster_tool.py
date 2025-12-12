"""
Active Roster Tool

Provides LLM agents with the ability to query active team rosters
from the database. This allows agents to know which players are
currently on a team's roster.
"""

import json
from typing import Dict, Any

from src.tools.base import BaseTool
from src.services.roster_sync import RosterSyncService


class ActiveRosterTool(BaseTool):
    """
    Tool for retrieving active team rosters from the database.
    
    Usage by LLM:
        When asked about a team's players, current squad, or who plays
        for a specific team, use this tool to get the roster.
    
    Returns:
        JSON with team name, league, and list of players with positions.
    """
    
    def __init__(self):
        """Initialize with roster service."""
        self.roster_service = RosterSyncService()
    
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
    
    def execute(self, team: str, league: str) -> str:
        """
        Fetch the active roster for a team from the database.
        
        Args:
            team: Team name
            league: League name
            
        Returns:
            JSON string with roster data
        """
        try:
            db_team_name = self.team_name_lookup(team)
            roster = self.roster_service.get_active_roster(db_team_name, league)
            
            # Format for LLM consumption
            players = [
                {
                    "name": player.get("player_name"),
                    "position": player.get("position")
                }
                for player in roster
            ]
            
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
                "league": league
            })
    
    def team_name_lookup(self, team: str) -> str:
        """
        Match the provided team name with the team name in the database.
        """
        team_name_lookup = {
            "Liverpool": "Liverpool FC",
        }
        return team_name_lookup.get(team, team)
