"""
Roster Update Service

This module orchestrates the full roster update flow:
1. Fetch active teams from the database (team registry)
2. Scrape each team's roster from Transfermarkt
3. Sync scraped data with the database

This is the main entry point for roster updates, whether triggered
manually or by a scheduled job.
"""

import asyncio
from typing import List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone

from database import session_scope
from database.models.team import Team
from src.services.roster_sync import RosterSyncService
from src.services.transfermarkt_scraper import TransfermarktScraper, ScraperConfig


@dataclass
class UpdateResult:
    """
    Result of a full roster update operation.
    
    Attributes:
        team_name: Name of the team
        league: League name
        success: Whether the update succeeded
        players_added: List of players added
        players_removed: List of players removed
        players_unchanged: Count of unchanged players
        error: Error message if failed
        duration_seconds: How long the update took
    """
    team_name: str
    league: str
    success: bool
    players_added: List[str] = field(default_factory=list)
    players_removed: List[str] = field(default_factory=list)
    players_unchanged: int = 0
    error: Optional[str] = None
    duration_seconds: float = 0.0
    
    def __str__(self) -> str:
        if self.success:
            return (
                f"✅ {self.team_name}: +{len(self.players_added)} added, "
                f"-{len(self.players_removed)} removed, "
                f"={self.players_unchanged} unchanged "
                f"({self.duration_seconds:.1f}s)"
            )
        else:
            return f"❌ {self.team_name}: {self.error}"


@dataclass 
class BatchUpdateResult:
    """
    Result of updating multiple teams.
    
    Attributes:
        results: Individual results for each team
        total_teams: Total teams attempted
        successful: Count of successful updates
        failed: Count of failed updates
        started_at: When the batch started
        completed_at: When the batch completed
    """
    results: List[UpdateResult]
    total_teams: int
    successful: int
    failed: int
    started_at: datetime
    completed_at: datetime
    
    @property
    def duration_seconds(self) -> float:
        return (self.completed_at - self.started_at).total_seconds()
    
    def __str__(self) -> str:
        return (
            f"Batch Update: {self.successful}/{self.total_teams} succeeded, "
            f"{self.failed} failed ({self.duration_seconds:.1f}s total)"
        )


class RosterUpdateService:
    """
    Service that orchestrates roster updates from Transfermarkt.
    
    Combines the scraper and sync services to provide a complete
    roster update workflow.
    
    Usage:
        service = RosterUpdateService()
        
        # Update a single team
        result = await service.update_team_by_name("Arsenal", "Premier League")
        
        # Update all active teams
        batch_result = await service.update_all_teams()
    """
    
    def __init__(
        self,
        scraper_config: Optional[ScraperConfig] = None
    ):
        """
        Initialize the roster update service.
        
        Args:
            scraper_config: Optional configuration for the scraper
        """
        self.scraper = TransfermarktScraper(config=scraper_config)
        self.sync_service = RosterSyncService()
    
    def get_active_teams(self) -> List[Team]:
        """
        Get all active teams from the database.
        
        Returns:
            List of Team objects that are active and have Transfermarkt data
        """
        with session_scope() as session:
            teams = session.query(Team).filter(
                Team.is_active.is_(True),
                Team.transfermarkt_id.isnot(None),
                Team.transfermarkt_slug.isnot(None)
            ).all()
            
            # Detach from session by converting to dict and back
            # This prevents issues when session closes
            return [self._detach_team(t) for t in teams]
    
    def _detach_team(self, team: Team) -> Team:
        """Create a detached copy of a team object."""
        return Team(
            id=team.id,
            team_name=team.team_name,
            league=team.league,
            country=team.country,
            transfermarkt_id=team.transfermarkt_id,
            transfermarkt_slug=team.transfermarkt_slug,
            is_active=team.is_active
        )
    
    def get_team_by_name(self, team_name: str, league: str) -> Optional[Team]:
        """
        Get a specific team from the database.
        
        Args:
            team_name: Name of the team
            league: League name
            
        Returns:
            Team object or None if not found
        """
        with session_scope() as session:
            team = session.query(Team).filter(
                Team.team_name == team_name,
                Team.league == league
            ).first()
            
            return self._detach_team(team) if team else None
    
    async def update_team(self, team: Team) -> UpdateResult:
        """
        Update a single team's roster.
        
        Args:
            team: Team object with Transfermarkt data
            
        Returns:
            UpdateResult with details of the update
        """
        start_time = datetime.now(timezone.utc)
        
        # Validate team has required data
        if not team.transfermarkt_id or not team.transfermarkt_slug:
            return UpdateResult(
                team_name=team.team_name,
                league=team.league,
                success=False,
                error="Missing Transfermarkt ID or slug"
            )
        
        try:
            # 1. Scrape roster from Transfermarkt
            print(f"\n🔄 Updating {team.team_name} ({team.league})...")
            players = await self.scraper.get_squad(
                team_slug=team.transfermarkt_slug,
                team_id=team.transfermarkt_id
            )
            
            if not players:
                return UpdateResult(
                    team_name=team.team_name,
                    league=team.league,
                    success=False,
                    error="No players found on Transfermarkt"
                )
            
            # 2. Sync with database
            sync_result = self.sync_service.sync_roster(
                team=team.team_name,
                league=team.league,
                scraped_players=players
            )
            
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # 3. Check for sync errors
            if sync_result.errors:
                return UpdateResult(
                    team_name=team.team_name,
                    league=team.league,
                    success=False,
                    error=f"Sync errors: {', '.join(sync_result.errors)}",
                    duration_seconds=duration
                )
            
            return UpdateResult(
                team_name=team.team_name,
                league=team.league,
                success=True,
                players_added=sync_result.added,
                players_removed=sync_result.removed,
                players_unchanged=sync_result.unchanged,
                duration_seconds=duration
            )
            
        except Exception as e:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            return UpdateResult(
                team_name=team.team_name,
                league=team.league,
                success=False,
                error=str(e),
                duration_seconds=duration
            )
    
    async def update_team_by_name(
        self,
        team_name: str,
        league: str
    ) -> UpdateResult:
        """
        Update a team's roster by name.
        
        Args:
            team_name: Name of the team
            league: League name
            
        Returns:
            UpdateResult with details of the update
        """
        team = self.get_team_by_name(team_name, league)
        
        if not team:
            return UpdateResult(
                team_name=team_name,
                league=league,
                success=False,
                error="Team not found in registry"
            )
        
        return await self.update_team(team)
    
    async def update_all_teams(self) -> BatchUpdateResult:
        """
        Update rosters for all active teams.
        
        Returns:
            BatchUpdateResult with results for all teams
        """
        started_at = datetime.now(timezone.utc)
        teams = self.get_active_teams()
        
        print(f"\n{'='*60}")
        print(f"Starting batch roster update for {len(teams)} teams")
        print(f"{'='*60}")
        
        results = []
        for team in teams:
            result = await self.update_team(team)
            results.append(result)
            print(f"  {result}")
        
        completed_at = datetime.now(timezone.utc)
        
        successful = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        
        batch_result = BatchUpdateResult(
            results=results,
            total_teams=len(teams),
            successful=successful,
            failed=failed,
            started_at=started_at,
            completed_at=completed_at
        )
        
        print(f"\n{'='*60}")
        print(f"Batch complete: {batch_result}")
        print(f"{'='*60}")
        
        return batch_result
    
    async def update_league(self, league: str) -> BatchUpdateResult:
        """
        Update rosters for all teams in a specific league.
        
        Args:
            league: League name to update
            
        Returns:
            BatchUpdateResult with results for league teams
        """
        started_at = datetime.now(timezone.utc)
        
        with session_scope() as session:
            teams = session.query(Team).filter(
                Team.is_active.is_(True),
                Team.league == league,
                Team.transfermarkt_id.isnot(None)
            ).all()
            teams = [self._detach_team(t) for t in teams]
        
        print(f"\n{'='*60}")
        print(f"Updating {len(teams)} teams in {league}")
        print(f"{'='*60}")
        
        results = []
        for team in teams:
            result = await self.update_team(team)
            results.append(result)
            print(f"  {result}")
        
        completed_at = datetime.now(timezone.utc)
        
        return BatchUpdateResult(
            results=results,
            total_teams=len(teams),
            successful=sum(1 for r in results if r.success),
            failed=sum(1 for r in results if not r.success),
            started_at=started_at,
            completed_at=completed_at
        )


async def main():
    """
    Demo function showing the roster update service.
    """
    print("=" * 60)
    print("Roster Update Service - Demo")
    print("=" * 60)
    
    service = RosterUpdateService()
    
    # Check if we have any teams in the registry
    teams = service.get_active_teams()
    
    if not teams:
        print("\n⚠️  No teams found in registry!")
        print("\nTo test, first add a team to the database:")
        print("""
    from database import session_scope
    from database.models.team import Team
    
    with session_scope() as session:
        team = Team(
            team_name="Arsenal",
            league="Premier League",
            country="England",
            transfermarkt_id=11,
            transfermarkt_slug="fc-arsenal",
            is_active=True
        )
        session.add(team)
        """)
        return
    
    print(f"\n📋 Found {len(teams)} active teams in registry:")
    for team in teams:
        print(f"  - {team.team_name} ({team.league})")
    
    # Update all teams
    print("\n🔄 Starting roster updates...")
    batch_result = await service.update_all_teams()
    
    # Summary
    print("\n📊 Summary:")
    print(f"  Total teams: {batch_result.total_teams}")
    print(f"  Successful: {batch_result.successful}")
    print(f"  Failed: {batch_result.failed}")
    print(f"  Duration: {batch_result.duration_seconds:.1f}s")
    
    # Show any failures
    failed_results = [r for r in batch_result.results if not r.success]
    if failed_results:
        print("\n❌ Failed updates:")
        for r in failed_results:
            print(f"  - {r.team_name}: {r.error}")
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

