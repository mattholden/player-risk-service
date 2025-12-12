"""
Roster Sync Service

This module handles synchronization of team rosters between scraped data
and the database. It compares incoming roster data with stored active rosters
and updates accordingly (deactivating removed players, adding new ones).
"""

from datetime import datetime, timezone
from typing import List, Dict, Optional
from dataclasses import dataclass

from database import session_scope
from database.models.roster import Roster


@dataclass
class PlayerData:
    """
    Data structure for player information from scraping.
    
    Attributes:
        player_name: Name of the player
        position: Player position (e.g., "FW", "MF", "DF", "GK")
    """
    player_name: str
    position: Optional[str] = None


@dataclass
class SyncResult:
    """
    Result of a roster sync operation.
    
    Attributes:
        team: Team name that was synced
        league: League name
        added: List of player names that were added
        removed: List of player names that were deactivated
        unchanged: Count of players that remained unchanged
        errors: List of any errors encountered
    """
    team: str
    league: str
    added: List[str]
    removed: List[str]
    unchanged: int
    errors: List[str]
    
    def __str__(self) -> str:
        return (
            f"SyncResult({self.team} - {self.league}): "
            f"+{len(self.added)} added, -{len(self.removed)} removed, "
            f"={self.unchanged} unchanged"
        )


class RosterSyncService:
    """
    Service for synchronizing team rosters with the database.
    
    This service compares scraped roster data with the current active roster
    in the database and performs the necessary updates:
    - New players are added with is_active=True
    - Players no longer on the roster are deactivated (is_active=False, end_date set)
    - Existing players remain unchanged
    
    Usage:
        service = RosterSyncService()
        result = service.sync_roster(
            team="Arsenal",
            league="Premier League",
            scraped_players=[
                PlayerData(player_name="Bukayo Saka", position="RW"),
                PlayerData(player_name="Martin Odegaard", position="MF"),
            ]
        )
        print(result)
    """
    
    def __init__(self):
        """Initialize the roster sync service."""
        pass
    
    def sync_roster(
        self,
        team: str,
        league: str,
        scraped_players: List[PlayerData]
    ) -> SyncResult:
        """
        Sync scraped roster data with the database.
        
        Args:
            team: Team name (e.g., "Arsenal")
            league: League name (e.g., "Premier League")
            scraped_players: List of PlayerData from scraping
            
        Returns:
            SyncResult with details of what was added/removed/unchanged
        """
        added = []
        removed = []
        errors = []
        
        with session_scope() as session:
            # 1. Get current active roster from DB
            active_roster = session.query(Roster).filter(
                Roster.team == team,
                Roster.league == league,
                Roster.is_active.is_(True)
            ).all()
            
            # 2. Build lookup structures
            db_players = {r.player_name: r for r in active_roster}
            scraped_names = {p.player_name for p in scraped_players}
            scraped_lookup = {p.player_name: p for p in scraped_players}
            
            # 3. Find differences
            players_to_remove = set(db_players.keys()) - scraped_names
            players_to_add = scraped_names - set(db_players.keys())
            unchanged_count = len(scraped_names & set(db_players.keys()))
            
            # 4. Deactivate removed players
            for player_name in players_to_remove:
                try:
                    roster_entry = db_players[player_name]
                    roster_entry.deactivate()
                    removed.append(player_name)
                except Exception as e:
                    errors.append(f"Failed to deactivate {player_name}: {str(e)}")
            
            # 5. Add new players
            for player_name in players_to_add:
                try:
                    player_data = scraped_lookup[player_name]
                    new_entry = Roster(
                        player_name=player_name,
                        team=team,
                        league=league,
                        position=player_data.position,
                        is_active=True,
                        start_date=datetime.now(timezone.utc)
                    )
                    session.add(new_entry)
                    added.append(player_name)
                except Exception as e:
                    errors.append(f"Failed to add {player_name}: {str(e)}")
        
        return SyncResult(
            team=team,
            league=league,
            added=added,
            removed=removed,
            unchanged=unchanged_count,
            errors=errors
        )
    
    def get_active_roster(self, team: str, league: str) -> List[Dict]:
        """
        Get the current active roster for a team.
        
        Args:
            team: Team name
            league: League name
            
        Returns:
            List of roster entries as dictionaries
        """
        with session_scope() as session:
            roster = session.query(Roster).filter(
                Roster.team == team,
                Roster.league == league,
                Roster.is_active.is_(True)
            ).all()

            print(f"ROSTER FOUND: {roster}\n")
            
            return [r.to_dict() for r in roster]
    
    def get_player_history(self, player_name: str) -> List[Dict]:
        """
        Get the roster history for a specific player.
        
        Args:
            player_name: Name of the player
            
        Returns:
            List of all roster entries (active and inactive) for this player
        """
        with session_scope() as session:
            entries = session.query(Roster).filter(
                Roster.player_name == player_name
            ).order_by(Roster.start_date.desc()).all()
            
            return [e.to_dict() for e in entries]
    
    def bulk_add_roster(
        self,
        team: str,
        league: str,
        players: List[PlayerData]
    ) -> int:
        """
        Bulk add players to a roster (for initial population).
        
        This method adds all players without checking for existing entries.
        Use sync_roster for normal updates.
        
        Args:
            team: Team name
            league: League name
            players: List of PlayerData to add
            
        Returns:
            Number of players added
        """
        added_count = 0
        
        with session_scope() as session:
            for player in players:
                new_entry = Roster(
                    player_name=player.player_name,
                    team=team,
                    league=league,
                    position=player.position,
                    is_active=True,
                    start_date=datetime.now(timezone.utc)
                )
                session.add(new_entry)
                added_count += 1
        
        return added_count


def main():
    """
    Demo function showing roster sync usage with mock data.
    """
    print("=" * 60)
    print("Roster Sync Service - Demo")
    print("=" * 60 + "\n")
    
    service = RosterSyncService()
    
    # Mock scraped data - pretend we scraped Arsenal's roster
    mock_players = [
        PlayerData(player_name="Bukayo Saka", position="RW"),
        PlayerData(player_name="Martin Odegaard", position="CM"),
        PlayerData(player_name="Declan Rice", position="DM"),
        PlayerData(player_name="William Saliba", position="CB"),
        PlayerData(player_name="Gabriel Magalhaes", position="CB"),
        PlayerData(player_name="David Raya", position="GK"),
    ]
    
    team = "Arsenal"
    league = "Premier League"
    
    # First sync - should add all players
    print(f"🔄 First sync for {team}...")
    result = service.sync_roster(team, league, mock_players)
    print(f"   {result}")
    print(f"   Added: {result.added}")
    
    # Get current roster
    print(f"\n📋 Current active roster for {team}:")
    roster = service.get_active_roster(team, league)
    for player in roster:
        print(f"   - {player['player_name']} ({player['position']})")
    
    # Simulate a transfer - remove one player, add another
    print(f"\n🔄 Simulating transfer window...")
    updated_players = [
        PlayerData(player_name="Bukayo Saka", position="RW"),
        PlayerData(player_name="Martin Odegaard", position="CM"),
        PlayerData(player_name="Declan Rice", position="DM"),
        PlayerData(player_name="William Saliba", position="CB"),
        PlayerData(player_name="Gabriel Magalhaes", position="CB"),
        # David Raya removed
        PlayerData(player_name="Aaron Ramsdale", position="GK"),  # New player
    ]
    
    result = service.sync_roster(team, league, updated_players)
    print(f"   {result}")
    print(f"   Added: {result.added}")
    print(f"   Removed: {result.removed}")
    
    # Show player history for the transferred goalkeeper
    print(f"\n📜 Player history for David Raya:")
    history = service.get_player_history("David Raya")
    for entry in history:
        status = "Active" if entry['is_active'] else "Inactive"
        print(f"   - {entry['team']} ({status}): {entry['start_date']} to {entry['end_date'] or 'present'}")
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()

