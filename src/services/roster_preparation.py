"""
Roster Preparation Service - Batch preparation of team rosters.

This service prepares rosters for upcoming fixtures by:
1. Pulling fixtures from BigQuery
2. Identifying teams not in the database
3. Running interactive verification for new teams
4. Batch updating all rosters

This is meant to be run as a preparation step before the main alert pipeline,
either manually or as a scheduled job.

Usage:
    make prepare-rosters           # Full preparation pipeline
    make prepare-rosters-teams     # Only add missing teams (no roster update)
    
    # Or directly:
    python -m src.services.roster_preparation
    python -m src.services.roster_preparation --teams-only
    python -m src.services.roster_preparation --skip-verify
"""

import asyncio
from typing import List, Set, Optional
from dataclasses import dataclass

from dotenv import load_dotenv
load_dotenv()

from bigquery import ProjectionsService
from src.services.team_lookup import TeamLookupService
from src.services.roster_update import RosterUpdateService
from database import session_scope
from database.models.team import Team


@dataclass
class PreparationResult:
    """Result of the roster preparation process."""
    fixtures_found: int
    teams_found: int
    teams_already_registered: int
    teams_added: int
    teams_skipped: int  # User declined verification
    teams_not_found: int  # Not found on Transfermarkt
    rosters_updated: int
    rosters_failed: int


class RosterPreparationService:
    """
    Service for batch preparation of team rosters.
    
    Coordinates the process of:
    1. Fetching upcoming fixtures
    2. Identifying and registering new teams
    3. Updating rosters for all teams
    """
    
    def __init__(self):
        self.projections_service = ProjectionsService()
        self.team_lookup_service = TeamLookupService()
        self.roster_update_service = RosterUpdateService()
    
    def get_fixtures(self) -> List[dict]:
        """Fetch upcoming fixtures from BigQuery."""
        print("\n" + "=" * 60)
        print("📅 STEP 1: Fetching Fixtures from BigQuery")
        print("=" * 60)
        
        fixtures = self.projections_service.get_upcoming_fixtures()
        
        print(f"\n   Found {len(fixtures)} fixtures")
        return fixtures
    
    def extract_teams_from_fixtures(self, fixtures: List[dict]) -> dict:
        """
        Extract unique team names with their leagues from fixtures.
        
        Returns:
            dict mapping team_name -> league
        """
        teams = {}  # team_name -> league
        
        for fixture in fixtures:
            fixture_str = fixture.get('fixture', '')
            league = fixture.get('league', 'Premier League')  # Fallback
            
            # Parse "Team A vs Team B" format
            if ' vs ' in fixture_str:
                parts = fixture_str.split(' vs ')
                if len(parts) == 2:
                    team1 = parts[0].strip()
                    team2 = parts[1].strip()
                    # Store team with its league
                    if team1 not in teams:
                        teams[team1] = league
                    if team2 not in teams:
                        teams[team2] = league
        
        print(f"\n   Extracted {len(teams)} unique teams from fixtures")
        return teams
    
    def get_registered_teams(self) -> Set[str]:
        """Get team names that are already in the database."""
        with session_scope() as session:
            teams = session.query(Team.team_name).filter(
                Team.transfermarkt_id.isnot(None)
            ).all()
            return {t[0] for t in teams}
    
    def find_missing_teams(self, fixture_teams: dict) -> List[tuple]:
        """
        Find teams that are in fixtures but not registered.
        
        Args:
            fixture_teams: dict mapping team_name -> league
            
        Returns:
            List of (team_name, league) tuples for missing teams
        """
        registered = self.get_registered_teams()
        
        # Simple matching - check if any registered team name contains/matches
        missing = []
        for team, league in fixture_teams.items():
            team_lower = team.lower()
            found = False
            for reg_team in registered:
                reg_lower = reg_team.lower()
                # Check for exact match or if one contains the other
                if team_lower == reg_lower or team_lower in reg_lower or reg_lower in team_lower:
                    found = True
                    break
            if not found:
                missing.append((team, league))
        
        # Sort by team name
        return sorted(missing, key=lambda x: x[0])
    
    async def register_missing_teams(
        self,
        missing_teams: List[tuple],
        verify: bool = True
    ) -> dict:
        """
        Register missing teams with interactive verification.
        
        Args:
            missing_teams: List of (team_name, league) tuples to register
            verify: Whether to open browser for verification
            
        Returns:
            dict with counts: added, skipped, not_found
        """
        print("\n" + "=" * 60)
        print("📝 STEP 2: Registering Missing Teams")
        print("=" * 60)
        
        if not missing_teams:
            print("\n   ✅ All teams already registered!")
            return {"added": 0, "skipped": 0, "not_found": 0}
        
        print(f"\n   Found {len(missing_teams)} teams to register:")
        for i, (team, league) in enumerate(missing_teams, 1):
            print(f"      {i}. {team} ({league})")
        
        results = {"added": 0, "skipped": 0, "not_found": 0}
        
        for i, (team_name, league) in enumerate(missing_teams, 1):
            print(f"\n{'─' * 60}")
            print(f"   [{i}/{len(missing_teams)}] Processing: {team_name} ({league})")
            print(f"{'─' * 60}")
            
            try:
                team = await self.team_lookup_service.lookup_and_add(
                    team_name=team_name,
                    league=league,
                    verify=verify
                )
                
                if team:
                    results["added"] += 1
                else:
                    # User declined or not found
                    # Check if it was a user decline vs not found
                    lookup_result = await self.team_lookup_service.lookup_team(
                        team_name, league
                    )
                    if lookup_result:
                        results["skipped"] += 1  # User declined
                    else:
                        results["not_found"] += 1
                        print(f"   ⚠️  Could not find {team_name} on Transfermarkt")
                        print(f"      Try a different name or add manually later")
                        
            except Exception as e:
                print(f"   ❌ Error processing {team_name}: {e}")
                results["not_found"] += 1
        
        print(f"\n{'─' * 60}")
        print(f"   📊 Registration Summary:")
        print(f"      Added: {results['added']}")
        print(f"      Skipped (user declined): {results['skipped']}")
        print(f"      Not found: {results['not_found']}")
        
        return results
    
    async def update_all_rosters(self) -> dict:
        """Update rosters for all registered teams."""
        print("\n" + "=" * 60)
        print("🔄 STEP 3: Updating All Rosters")
        print("=" * 60)
        
        # Get all active teams with Transfermarkt data
        teams = self.roster_update_service.get_active_teams()
        
        if not teams:
            print("\n   ⚠️  No teams with Transfermarkt data found")
            return {"updated": 0, "failed": 0}
        
        print(f"\n   Updating rosters for {len(teams)} teams...")
        
        results = {"updated": 0, "failed": 0}
        
        for i, team in enumerate(teams, 1):
            print(f"\n   [{i}/{len(teams)}] {team.team_name}...")
            
            try:
                result = await self.roster_update_service.update_team(team)
                
                if result.success:
                    print(f"      ✅ +{len(result.players_added)} added, "
                          f"-{len(result.players_removed)} removed, "
                          f"={result.players_unchanged} unchanged")
                    results["updated"] += 1
                else:
                    print(f"      ⚠️  {result.error}")
                    results["failed"] += 1
                    
            except Exception as e:
                print(f"      ❌ Error: {e}")
                results["failed"] += 1
        
        print(f"\n{'─' * 60}")
        print(f"   📊 Roster Update Summary:")
        print(f"      Updated: {results['updated']}")
        print(f"      Failed: {results['failed']}")
        
        return results
    
    async def run(
        self,
        verify: bool = True,
        teams_only: bool = False,
        league_filter: Optional[str] = None
    ) -> PreparationResult:
        """
        Run the full roster preparation pipeline.
        
        Args:
            verify: Whether to verify teams in browser
            teams_only: If True, only register teams (skip roster update)
            league_filter: If set, only process fixtures from this league
            
        Returns:
            PreparationResult with summary statistics
        """
        print("\n" + "=" * 60)
        print("🚀 ROSTER PREPARATION PIPELINE")
        print("=" * 60)
        print(f"   Verify in browser: {verify}")
        print(f"   Teams only: {teams_only}")
        if league_filter:
            print(f"   League filter: {league_filter}")
        
        # Step 1: Get fixtures
        fixtures = self.get_fixtures()
        
        if not fixtures:
            print("\n❌ No fixtures found. Exiting.")
            return PreparationResult(
                fixtures_found=0, teams_found=0,
                teams_already_registered=0, teams_added=0,
                teams_skipped=0, teams_not_found=0,
                rosters_updated=0, rosters_failed=0
            )
        
        # Filter by league if specified
        if league_filter:
            original_count = len(fixtures)
            fixtures = [f for f in fixtures if league_filter.lower() in f.get('league', '').lower()]
            print(f"\n   Filtered to {len(fixtures)} fixtures (from {original_count}) for '{league_filter}'")
        
        if not fixtures:
            print("\n❌ No fixtures match the league filter. Exiting.")
            return PreparationResult(
                fixtures_found=0, teams_found=0,
                teams_already_registered=0, teams_added=0,
                teams_skipped=0, teams_not_found=0,
                rosters_updated=0, rosters_failed=0
            )
        
        # Extract teams with their leagues
        all_teams = self.extract_teams_from_fixtures(fixtures)
        missing_teams = self.find_missing_teams(all_teams)
        already_registered = len(all_teams) - len(missing_teams)
        
        print(f"\n   Teams already registered: {already_registered}")
        print(f"   Teams to register: {len(missing_teams)}")
        
        # Step 2: Register missing teams (each with its own league)
        reg_results = await self.register_missing_teams(
            missing_teams, verify=verify
        )
        
        # Step 3: Update rosters (unless teams_only)
        roster_results = {"updated": 0, "failed": 0}
        if not teams_only:
            roster_results = await self.update_all_rosters()
        else:
            print("\n⏭️  Skipping roster update (--teams-only)")
        
        # Summary
        result = PreparationResult(
            fixtures_found=len(fixtures),
            teams_found=len(all_teams),
            teams_already_registered=already_registered,
            teams_added=reg_results["added"],
            teams_skipped=reg_results["skipped"],
            teams_not_found=reg_results["not_found"],
            rosters_updated=roster_results["updated"],
            rosters_failed=roster_results["failed"]
        )
        
        print("\n" + "=" * 60)
        print("✅ PREPARATION COMPLETE")
        print("=" * 60)
        print(f"   Fixtures found: {result.fixtures_found}")
        print(f"   Teams in fixtures: {result.teams_found}")
        print(f"   Teams already registered: {result.teams_already_registered}")
        print(f"   Teams added: {result.teams_added}")
        print(f"   Teams skipped: {result.teams_skipped}")
        print(f"   Teams not found: {result.teams_not_found}")
        if not teams_only:
            print(f"   Rosters updated: {result.rosters_updated}")
            print(f"   Rosters failed: {result.rosters_failed}")
        
        return result


async def main():
    """CLI entry point."""
    import sys
    
    # Parse arguments
    teams_only = "--teams-only" in sys.argv
    skip_verify = "--skip-verify" in sys.argv
    
    # Check for --league argument
    league_filter = None
    for i, arg in enumerate(sys.argv):
        if arg == "--league" and i + 1 < len(sys.argv):
            league_filter = sys.argv[i + 1]
    
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Roster Preparation Pipeline")
        print("\nUsage: python -m src.services.roster_preparation [options]")
        print("\nOptions:")
        print("  --teams-only      Only register missing teams, skip roster update")
        print("  --skip-verify     Skip browser verification (use with caution)")
        print("  --league NAME     Only process fixtures from this league")
        print("  --help, -h        Show this help message")
        print("\nExamples:")
        print('  python -m src.services.roster_preparation --league "Premier League"')
        print('  python -m src.services.roster_preparation --league "La Liga" --teams-only')
        print("\nMake commands:")
        print("  make prepare-rosters                              Full preparation (all leagues)")
        print("  make prepare-rosters-epl                          Premier League only")
        print("  make prepare-rosters-teams                        Teams only (all leagues)")
        print('  make prepare-rosters-league LEAGUE="La Liga"      Specific league')
        return
    
    service = RosterPreparationService()
    await service.run(
        verify=not skip_verify,
        teams_only=teams_only,
        league_filter=league_filter
    )


if __name__ == "__main__":
    asyncio.run(main())

