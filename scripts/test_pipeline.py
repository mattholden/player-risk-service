"""
Test script for the projection alert pipeline.

Tests each step of the pipeline incrementally:
- Step 1: Fetch fixtures from BigQuery
- Step 2-3: Update rosters for fixtures
- Step 4-5: Run agent pipeline
- Step 6-7: Enrich projections and push to BigQuery

Usage:
    python -m scripts.test_pipeline
    python -m scripts.test_pipeline --step 1
    python -m scripts.test_pipeline --step 2 --fixture "Arsenal vs Brentford"
    python -m scripts.test_pipeline --step 6 --fixture "Arsenal vs Brentford"
"""

import asyncio
import argparse
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from bigquery import ProjectionsService
from src.services.roster_update import RosterUpdateService
from src.services.agent_pipeline import AgentPipeline
from database.services import AlertService


def test_step1_fixtures():
    """Test Step 1: Fetch fixtures from BigQuery."""
    print("\n" + "="*60)
    print("TEST: Step 1 - Fetch Fixtures from BigQuery")
    print("="*60)
    
    service = ProjectionsService()
    fixtures = service.get_upcoming_fixtures()
    
    print(f"\n✅ Found {len(fixtures)} fixtures")
    
    # Show first 5
    print("\nFirst 5 fixtures:")
    for i, f in enumerate(fixtures[:5], 1):
        print(f"   {i}. {f['fixture']} @ {f['match_time']}")
    
    return fixtures


async def test_step2_roster_update(fixture: str):
    """Test Step 2-3: Update rosters for a fixture."""
    print("\n" + "="*60)
    print(f"TEST: Step 2-3 - Update Rosters")
    print(f"Fixture: {fixture}")
    print("="*60)
    
    service = RosterUpdateService()
    results = await service.update_fixture_rosters(fixture)
    
    print(f"\n📊 Results:")
    for result in results:
        if result.success:
            print(f"   ✅ {result.team_name}")
            print(f"      Added: {result.players_added[:3]}..." if len(result.players_added) > 3 else f"      Added: {result.players_added}")
            print(f"      Removed: {result.players_removed}")
            print(f"      Unchanged: {result.players_unchanged}")
        else:
            print(f"   ❌ {result.team_name}: {result.error}")
    
    return results


def test_step4_agents(fixture: str, match_time: str = None):
    """Test Step 4-5: Run agent pipeline for a fixture."""
    print("\n" + "="*60)
    print(f"TEST: Step 4-5 - Run Agent Pipeline")
    print(f"Fixture: {fixture}")
    print("="*60)
    
    # Parse or default match_time
    if match_time:
        try:
            if "T" in match_time:
                fixture_date = datetime.fromisoformat(match_time)
            else:
                fixture_date = datetime.strptime(match_time, "%Y-%m-%d")
                fixture_date = fixture_date.replace(hour=12, minute=0)
        except ValueError:
            fixture_date = datetime.now()
    else:
        fixture_date = datetime.now()
    
    print(f"   Fixture date: {fixture_date}")
    
    pipeline = AgentPipeline()
    
    print("\n🤖 Running agent pipeline...")
    print("   (This may take a minute - agents are researching injuries)")
    
    alerts = pipeline.run_and_save(fixture, fixture_date)
    
    print(f"\n📊 Results:")
    print(f"   Total alerts: {len(alerts)}")
    
    if alerts:
        print("\n   Alerts by level:")
        from collections import Counter
        levels = Counter(a.alert_level.value for a in alerts)
        for level, count in sorted(levels.items()):
            print(f"      {level}: {count}")
        
        print("\n   Sample alerts:")
        for alert in alerts[:5]:
            print(f"      • {alert.player_name} ({alert.alert_level.value})")
            print(f"        {alert.description[:80]}...")
    
    return alerts


def test_step6_enrichment(fixture: str, dry_run: bool = False):
    """Test Step 6-7: Enrich projections and push to BigQuery."""
    print("\n" + "="*60)
    print(f"TEST: Step 6-7 - BigQuery Enrichment")
    print(f"Fixture: {fixture}")
    print(f"Dry run: {dry_run}")
    print("="*60)
    
    alert_service = AlertService()
    projections_service = ProjectionsService()
    
    # Step 6a: Fetch latest alerts from database (one per player/fixture)
    print("\n🔍 Fetching latest alerts from database...")
    fixtures = [fixture]
    db_alerts = alert_service.get_latest_alerts_for_fixtures(fixtures)
    
    print(f"   Found {len(db_alerts)} alerts")
    
    if db_alerts:
        print("\n   Alerts by level:")
        from collections import Counter
        levels = Counter(a.alert_level.value for a in db_alerts)
        for level, count in sorted(levels.items()):
            print(f"      {level}: {count}")
        
        print("\n   Sample alerts:")
        for alert in db_alerts[:3]:
            print(f"      • {alert.player_name} ({alert.alert_level.value})")
    
    # Step 6b: Fetch projections from BigQuery
    print("\n📊 Fetching projections from BigQuery...")
    projections = projections_service.get_all_projections_for_fixtures(fixtures)
    
    if projections.empty:
        print("   ❌ No projections found")
        return None
    
    print(f"   Found {len(projections)} projection rows")
    
    # Show unique players
    if 'player_name' in projections.columns:
        unique_players = projections['player_name'].nunique()
        print(f"   Unique players: {unique_players}")
    
    # Step 6c: Enrich projections
    print("\n🔗 Enriching projections with alerts...")
    enriched = projections_service.enrich_with_alerts(projections, db_alerts)
    
    # Show enrichment stats
    if 'alert_level' in enriched.columns:
        matched = enriched[enriched['alert_level'].notna()]
        unmatched = enriched[enriched['alert_level'].isna()]
        print(f"\n   📈 Enrichment results:")
        print(f"      Total rows: {len(enriched)}")
        print(f"      Rows with alerts: {len(matched)}")
        print(f"      Rows with null (healthy): {len(unmatched)}")
        
        if len(matched) > 0:
            print("\n   Alert breakdown:")
            alert_counts = enriched['alert_level'].value_counts(dropna=False)
            for level, count in alert_counts.items():
                level_display = level if level is not None else "null (healthy)"
                print(f"      {level_display}: {count}")
    
    # Step 7: Push to BigQuery (if not dry run)
    if not dry_run:
        print(f"\n📤 Pushing all {len(enriched)} projections to BigQuery...")
        print("   (Healthy players will have null alert columns)")
        projections_service.push_enriched_projections(enriched)
        print("   ✅ Push complete!")
    else:
        print("\n🔒 Dry run - skipping BigQuery write")
    
    return enriched


async def test_full_flow(fixture: str = None):
    """Test Steps 1 + 2-3 together."""
    print("\n" + "="*60)
    print("TEST: Full Flow (Steps 1 + 2-3)")
    print("="*60)
    
    # Step 1: Get fixtures
    fixtures = test_step1_fixtures()
    
    if not fixtures:
        print("❌ No fixtures found")
        return
    
    # Use provided fixture or pick the first one
    if fixture:
        target_fixture = fixture
    else:
        target_fixture = fixtures[0]['fixture']
        print(f"\n📍 Using first fixture: {target_fixture}")
    
    # Step 2-3: Update rosters
    await test_step2_roster_update(target_fixture)
    
    print("\n" + "="*60)
    print("✅ Test complete!")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(description="Test pipeline steps")
    parser.add_argument(
        "--step",
        type=int,
        choices=[1, 2, 4, 6],
        help="Test specific step only (1=fixtures, 2=roster update, 4=agents, 6=enrichment)"
    )
    parser.add_argument(
        "--fixture",
        type=str,
        default=None,
        help="Fixture to test (e.g., 'Arsenal vs Brentford')"
    )
    parser.add_argument(
        "--match-time",
        type=str,
        default=None,
        help="Match time (e.g., '2025-12-06')"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="For step 6: don't push to BigQuery"
    )
    
    args = parser.parse_args()
    
    if args.step == 1:
        test_step1_fixtures()
    elif args.step == 2:
        fixture = args.fixture or "Arsenal vs Brentford"
        asyncio.run(test_step2_roster_update(fixture))
    elif args.step == 4:
        fixture = args.fixture or "Arsenal vs Brentford"
        test_step4_agents(fixture, args.match_time)
    elif args.step == 6:
        fixture = args.fixture or "Arsenal vs Brentford"
        test_step6_enrichment(fixture, dry_run=args.dry_run)
    else:
        asyncio.run(test_full_flow(args.fixture))


if __name__ == "__main__":
    main()

