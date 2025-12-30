"""
Test script to run the full alerts pipeline for a single fixture.

This script allows you to:
1. View all available fixtures from BigQuery
2. Select a specific fixture to process
3. Run the complete pipeline (agents + alerts + enrichment) for that fixture
4. Troubleshoot and verify results between fixtures

Usage:
    # List all available fixtures
    python -m scripts.test_fixture_pipeline --list
    
    # Run a specific fixture by name
    python -m scripts.test_fixture_pipeline --fixture "Arsenal vs Brentford"
    
    # Run a specific fixture by index
    python -m scripts.test_fixture_pipeline --index 0
    
    # Dry run (don't push to BigQuery)
    python -m scripts.test_fixture_pipeline --fixture "Arsenal vs Brentford" --dry-run
"""

import asyncio
import sys
import argparse
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pipeline import ProjectionAlertPipeline
from bigquery import BigQueryClient, ProjectionsService
from database.services import AlertService


async def list_fixtures(league_filter: str = None):
    """List all available fixtures from BigQuery (upcoming only)."""
    print("\n" + "=" * 80)
    print("📋 AVAILABLE FIXTURES (Upcoming Only)")
    if league_filter:
        print(f"   (Filtered to: {league_filter})")
    print("=" * 80)
    
    client = BigQueryClient()
    service = ProjectionsService(client)
    
    try:
        all_fixtures = service.get_upcoming_fixtures()
        
        if not all_fixtures:
            print("\n⚠️  No fixtures found in BigQuery")
            return []
        
        if league_filter:
            fixtures = [
                f for f in all_fixtures 
                if league_filter.lower() in f.get('league', '').lower()
            ]
            
            if not fixtures:
                print(f"\n⚠️  No fixtures found for league: {league_filter}")
                print(f"\nAvailable leagues:")
                leagues = sorted(set(f.get('league', 'Unknown') for f in all_fixtures))
                for league in leagues:
                    count = sum(1 for f in all_fixtures if f.get('league') == league)
                    print(f"  - {league} ({count} fixtures)")
                return []
        else:
            fixtures = all_fixtures
        
        print(f"\nFound {len(fixtures)} upcoming fixture(s):\n")
        
        for i, fixture_data in enumerate(fixtures):
            fixture_name = fixture_data['fixture']
            match_time = fixture_data.get('match_time', 'Unknown')
            league = fixture_data.get('league', 'Unknown')
            
            print(f"[{i}] {fixture_name}")
            print(f"    League: {league}")
            print(f"    Match Time: {match_time}")
            print()
        
        return fixtures
        
    except Exception as e:
        print(f"\n❌ Error fetching fixtures: {e}")
        import traceback
        traceback.print_exc()
        return []


async def run_fixture_pipeline(
    fixture_name: str,
    fixture_date: datetime,
    league: str,
    dry_run: bool = False
):
    """Run the complete pipeline for a single fixture."""
    print("\n" + "=" * 80)
    print(f"🎯 RUNNING PIPELINE FOR: {fixture_name}")
    print("=" * 80)
    print(f"League: {league}")
    print(f"Date: {fixture_date}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print("=" * 80)
    
    pipeline = ProjectionAlertPipeline(dry_run=dry_run)
    alert_service = AlertService()
    
    # Step 1: Parse teams from fixture
    print("\n📝 Step 1: Parsing fixture teams...")
    teams = fixture_name.split(' vs ')
    if len(teams) != 2:
        # Try alternate separators
        teams = fixture_name.split(' v ')
    
    if len(teams) != 2:
        print(f"   ❌ Could not parse fixture '{fixture_name}' into two teams")
        print(f"   Expected format: 'Team A vs Team B' or 'Team A v Team B'")
        return
    
    home_team, away_team = [t.strip() for t in teams]
    print(f"   Home: {home_team}")
    print(f"   Away: {away_team}")
    
    # Step 2: Update rosters for both teams
    print("\n📝 Step 2: Updating team rosters...")
    for team_name in [home_team, away_team]:
        print(f"\n   Updating roster for {team_name}...")
        result = await pipeline.roster_update_service.update_team_by_name(
            team_name, league
        )
        
        if result.success:
            added = len(result.players_added) if result.players_added else 0
            removed = len(result.players_removed) if result.players_removed else 0
            unchanged = result.players_unchanged or 0
            total = added + unchanged
            
            print(f"   ✅ {team_name}: {total} players total")
            if added > 0:
                print(f"      Added: {added}")
            if removed > 0:
                print(f"      Removed: {removed}")
            if unchanged > 0:
                print(f"      Unchanged: {unchanged}")
        else:
            print(f"   ⚠️  {team_name}: {result.error}")
            print(f"   Note: Agent will attempt to find roster online if needed")
    
    # Step 3: Run agentic pipeline for the fixture
    print(f"\n📝 Step 3: Running agentic pipeline...")
    print(f"   Fixture: {fixture_name}")
    print(f"   This will run Research → Analyst → Shark agents")
    
    try:
        alerts = pipeline.run_agents_for_fixture(fixture_name, fixture_date)
        
        print(f"\n   ✅ Generated {len(alerts)} alert(s)")
        
        if alerts:
            print(f"\n   Alert breakdown:")
            from collections import Counter
            alert_counts = Counter(alert.alert_level.value for alert in alerts)
            for level, count in sorted(alert_counts.items()):
                print(f"      {level}: {count}")
            
            print(f"\n   Sample alerts:")
            for i, alert in enumerate(alerts[:5], 1):
                print(f"      {i}. {alert.player_name} - {alert.alert_level.value}")
                print(f"         {alert.description[:80]}...")
        else:
            print(f"\n   ℹ️  No alerts generated for this fixture")
            print(f"   The enrichment step will still run, but all projections will have null alert values")
    
    except Exception as e:
        print(f"\n   ❌ Error running agents: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 4: Check alerts in database
    print(f"\n📝 Step 4: Verifying alerts in database...")
    db_alerts = alert_service.get_alerts_for_fixture(fixture_name)
    print(f"   Found {len(db_alerts)} alert(s) in database for this fixture")
    
    # Step 5: Enrich BigQuery projections with alerts
    print(f"\n📝 Step 5: Enriching BigQuery projections...")
    print(f"   Pulling projections for fixture: {fixture_name}")
    
    try:
        count = pipeline.enrich_and_push_projections(
            fixtures=[fixture_name],
            push_all=True  # Push all projections, not just alerted ones
        )
        
        print(f"\n   ✅ Processed and pushed {count} projection(s)")
        
        if dry_run:
            print(f"\n   🔒 DRY RUN: Data was NOT pushed to BigQuery")
        else:
            print(f"\n   💾 Data successfully pushed to BigQuery")
            print(f"   Destination: {pipeline.projections_service.dest_table_id}")
    
    except Exception as e:
        print(f"\n   ❌ Error enriching projections: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Summary
    print("\n" + "=" * 80)
    print("✅ PIPELINE COMPLETE")
    print("=" * 80)
    print(f"Fixture: {fixture_name}")
    print(f"Alerts Generated: {len(alerts)}")
    print(f"Projections Enriched: {count}")
    
    if not dry_run:
        print(f"\nNext steps:")
        print(f"1. Check BigQuery destination table for enriched projections")
        print(f"2. Verify alert levels and descriptions are correctly populated")
        print(f"3. Review any projections with null alerts (healthy players)")
    else:
        print(f"\nRun without --dry-run flag to push to BigQuery")
    
    print("=" * 80 + "\n")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run the full alerts pipeline for a single fixture",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all available fixtures from BigQuery'
    )
    
    parser.add_argument(
        '--fixture',
        type=str,
        help='Fixture name (e.g., "Arsenal vs Brentford")'
    )
    
    parser.add_argument(
        '--index',
        type=int,
        help='Fixture index from the list (use --list to see indices)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run pipeline but do not push to BigQuery'
    )
    
    parser.add_argument(
        '--league',
        type=str,
        help='Filter fixtures by league (e.g., "Premier League")'
    )
    
    args = parser.parse_args()
    
    # List fixtures if requested
    if args.list or (not args.fixture and args.index is None):
        await list_fixtures(league_filter=args.league)
        return
    
    # Get fixture to run
    fixture_data = None
    
    if args.index is not None:
        # Run by index
        fixtures = await list_fixtures(league_filter=args.league)
        if 0 <= args.index < len(fixtures):
            fixture_data = fixtures[args.index]
        else:
            print(f"\n❌ Invalid index: {args.index}")
            print(f"   Valid indices: 0-{len(fixtures)-1}")
            return
    
    elif args.fixture:
        # Run by name - need to fetch fixtures to get match_time and league
        client = BigQueryClient()
        service = ProjectionsService(client)
        all_fixtures = service.get_upcoming_fixtures()
        
        # Filter out past fixtures
        now = datetime.now()
        filtered = []
        for f in all_fixtures:
            match_time = f.get('match_time')
            if match_time:
                if isinstance(match_time, datetime):
                    fixture_date = match_time
                elif isinstance(match_time, str):
                    try:
                        fixture_date = datetime.strptime(match_time[:10], "%Y-%m-%d")
                    except ValueError:
                        fixture_date = now
                else:
                    try:
                        fixture_date = datetime.combine(match_time, datetime.min.time())
                    except:
                        fixture_date = now
                
                if fixture_date >= now:
                    filtered.append(f)
            else:
                filtered.append(f)
        all_fixtures = filtered
        
        # Apply league filter if provided
        if args.league:
            fixtures = [
                f for f in all_fixtures 
                if args.league.lower() in f.get('league', '').lower()
            ]
        else:
            fixtures = all_fixtures
        
        # Find matching fixture
        for f in fixtures:
            if f['fixture'].lower() == args.fixture.lower():
                fixture_data = f
                break
        
        if not fixture_data:
            print(f"\n❌ Fixture not found: {args.fixture}")
            if args.league:
                print(f"   (in league: {args.league})")
            print(f"\nAvailable fixtures:")
            for f in fixtures:
                print(f"  - {f['fixture']}")
            return
    
    # Run the pipeline
    if fixture_data:
        await run_fixture_pipeline(
            fixture_name=fixture_data['fixture'],
            fixture_date=fixture_data.get('match_time', datetime.now()),
            league=fixture_data.get('league', 'Unknown'),
            dry_run=args.dry_run
        )


if __name__ == "__main__":
    asyncio.run(main())

