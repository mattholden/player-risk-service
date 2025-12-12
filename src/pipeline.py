"""
Main orchestration pipeline for projection risk alerts.

This is the primary entry point for running the full pipeline:
1. Fetch upcoming fixtures from BigQuery projections
2. Update rosters for each team in each fixture
3. Run the agentic pipeline to generate alerts
4. Save alerts to the database
5. Enrich projections with alerts and push to BigQuery

Usage:
    make pipeline
    make pipeline-dry-run
    make pipeline-fixtures
"""

import asyncio
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv  # noqa: E402
load_dotenv()

from bigquery import ProjectionsService  # noqa: E402
from src.services.roster_update import RosterUpdateService  # noqa: E402
from src.services.agent_pipeline import AgentPipeline  # noqa: E402


class ProjectionAlertPipeline:
    """
    Main orchestrator for the projection risk alert pipeline.
    
    Coordinates the full workflow from fetching fixtures to
    pushing enriched projections back to BigQuery.
    """
    
    def __init__(self, dry_run: bool = False):
        """
        Initialize the pipeline.
        
        Args:
            dry_run: If True, don't write to database or BigQuery
        """
        self.dry_run = dry_run
        self.projections_service = ProjectionsService()
        self.roster_update_service = RosterUpdateService()
        self.agent_pipeline = AgentPipeline()
    
    # =========================================================================
    # Step 1: Fetch Fixtures
    # =========================================================================
    
    def get_fixtures(self) -> list[dict]:
        """
        Fetch upcoming fixtures from BigQuery projections table.
        
        Returns:
            list[dict]: Fixtures with 'fixture' and 'match_time' keys
        """
        print("\n" + "="*60)
        print("📅 STEP 1: Fetching Fixtures")
        print("="*60)
        
        fixtures = self.projections_service.get_upcoming_fixtures()
        
        if not fixtures:
            print("⚠️  No fixtures found in projections table")
            return []
        
        print(f"\n📋 Found {len(fixtures)} fixtures:")
        for i, f in enumerate(fixtures, 1):
            print(f"   {i}. {f['fixture']} @ {f['match_time']}")
        
        return fixtures
    
    # =========================================================================
    # Step 2-3: Update Rosters
    # =========================================================================
    
    async def update_rosters_for_fixture(self, fixture: str) -> bool:
        """
        Update rosters for both teams in a fixture.
        
        Failures are logged but don't stop the pipeline - the agent has
        contingencies to find roster info from online sources.
        
        Args:
            fixture: Fixture string (e.g., "Arsenal vs Brentford")
            
        Returns:
            bool: True if at least one roster was updated successfully
        """
        print(f"\n🔄 Updating rosters for: {fixture}")
        
        results = await self.roster_update_service.update_fixture_rosters(fixture)
        
        # Return True if at least one team updated successfully
        successes = sum(1 for r in results if r.success)
        return successes > 0
    
    # =========================================================================
    # Step 4-5: Run Agent Pipeline
    # =========================================================================
    
    def run_agents_for_fixture(self, fixture: str, match_time: str) -> list:
        """
        Run the agentic pipeline for a fixture and save alerts.
        
        Args:
            fixture: Fixture string (e.g., "Arsenal vs Brentford")
            match_time: Match time string (e.g., "2025-12-06")
            
        Returns:
            list: Generated PlayerAlert objects
        """
        print(f"\n🤖 Running agents for: {fixture}")
        
        # Parse match_time string to datetime
        try:
            # Handle various date formats
            if "T" in match_time:
                fixture_date = datetime.fromisoformat(match_time)
            elif " " in match_time:
                fixture_date = datetime.strptime(match_time, "%Y-%m-%d %H:%M:%S")
            else:
                # Date only - default to noon
                fixture_date = datetime.strptime(match_time, "%Y-%m-%d")
                fixture_date = fixture_date.replace(hour=12, minute=0)
        except ValueError as e:
            print(f"   ⚠️  Could not parse match_time '{match_time}': {e}")
            fixture_date = datetime.now()
        
        # Run the agent pipeline
        if self.dry_run:
            print("   🔒 Dry run - skipping agent execution")
            return []
        
        try:
            alerts = self.agent_pipeline.run_and_save(fixture, fixture_date)
            print(f"   ✅ Generated {len(alerts)} alerts")
            return alerts
        except Exception as e:
            print(f"   ❌ Agent pipeline failed: {e}")
            return []
    
    # =========================================================================
    # Step 6-7: Enrich and Push (placeholder for now)
    # =========================================================================
    
    def enrich_and_push_projections(self) -> None:
        """
        Pull projections, match with alerts, and push enriched data.
        """
        # TODO: Implement in next iteration
        print("\n📤 Enriching projections and pushing to BigQuery")
        print("   ⏭️  [Not yet implemented - will add in Step 6-7]")
    
    # =========================================================================
    # Main Run Method
    # =========================================================================
    
    async def run_async(self, fixtures: Optional[list[dict]] = None) -> None:
        """
        Execute the full pipeline (async version).
        
        Args:
            fixtures: Optional list of fixtures to process. If not provided,
                     fetches from BigQuery.
        """
        start_time = datetime.now()
        
        print("\n" + "="*60)
        print("🚀 PROJECTION ALERT PIPELINE")
        print("="*60)
        print(f"   Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Dry run: {self.dry_run}")
        
        # Step 1: Get fixtures
        if fixtures is None:
            fixtures = self.get_fixtures()
        
        if not fixtures:
            print("\n❌ No fixtures to process. Exiting.")
            return
        
        # Steps 2-5: Process each fixture
        print("\n" + "="*60)
        print("⚙️  PROCESSING FIXTURES")
        print("="*60)
        
        all_alerts = []
        for i, fixture_data in enumerate(fixtures, 1):
            fixture = fixture_data['fixture']
            match_time = fixture_data['match_time']
            
            print(f"\n{'─'*60}")
            print(f"📍 Fixture {i}/{len(fixtures)}: {fixture}")
            print(f"   Match time: {match_time}")
            print(f"{'─'*60}")
            
            # Step 2-3: Update rosters
            await self.update_rosters_for_fixture(fixture)
            
            # Step 4-5: Run agents
            alerts = self.run_agents_for_fixture(fixture, match_time)
            all_alerts.extend(alerts)
        
        # Step 6-7: Enrich and push
        print("\n" + "="*60)
        print("📊 ENRICHMENT & EXPORT")
        print("="*60)
        
        if not self.dry_run:
            self.enrich_and_push_projections()
        else:
            print("\n🔒 Dry run - skipping BigQuery write")
        
        # Summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print("\n" + "="*60)
        print("✅ PIPELINE COMPLETE")
        print("="*60)
        print(f"   Fixtures processed: {len(fixtures)}")
        print(f"   Alerts generated: {len(all_alerts)}")
        print(f"   Duration: {duration:.1f} seconds")
        print(f"   Finished: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    def run(self, fixtures: Optional[list[dict]] = None) -> None:
        """
        Execute the full pipeline (sync wrapper).
        
        Args:
            fixtures: Optional list of fixtures to process. If not provided,
                     fetches from BigQuery.
        """
        asyncio.run(self.run_async(fixtures))


def main():
    """Entry point for running the pipeline."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run the projection alert pipeline"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without writing to database or BigQuery"
    )
    parser.add_argument(
        "--fixtures-only",
        action="store_true", 
        help="Only fetch and display fixtures, don't process"
    )
    
    args = parser.parse_args()
    
    pipeline = ProjectionAlertPipeline(dry_run=args.dry_run)
    
    if args.fixtures_only:
        pipeline.get_fixtures()
    else:
        pipeline.run()


if __name__ == "__main__":
    main()

