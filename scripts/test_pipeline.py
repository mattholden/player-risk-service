"""
Test script for the projection alert pipeline.

Tests each step of the pipeline incrementally:
- Step 1: Fetch fixtures from BigQuery
- Step 2-3: Update rosters for fixtures

Usage:
    python -m scripts.test_pipeline
    python -m scripts.test_pipeline --step 1
    python -m scripts.test_pipeline --step 2 --fixture "Arsenal vs Brentford"
"""

import asyncio
import argparse
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from bigquery import ProjectionsService
from src.services.roster_update import RosterUpdateService
from src.services.agent_pipeline import AgentPipeline


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
        choices=[1, 2, 4],
        help="Test specific step only (1=fixtures, 2=roster update, 4=agents)"
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
    
    args = parser.parse_args()
    
    if args.step == 1:
        test_step1_fixtures()
    elif args.step == 2:
        fixture = args.fixture or "Arsenal vs Brentford"
        asyncio.run(test_step2_roster_update(fixture))
    elif args.step == 4:
        fixture = args.fixture or "Arsenal vs Brentford"
        test_step4_agents(fixture, args.match_time)
    else:
        asyncio.run(test_full_flow(args.fixture))


if __name__ == "__main__":
    main()

