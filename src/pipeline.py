import asyncio
from datetime import datetime
from typing import Optional
import uuid

from dotenv import load_dotenv

load_dotenv()

from src.utils.run_id import get_run_id  # noqa: E402
from src.logging import get_logger  # noqa: E402
from bigquery import ProjectionsService  # noqa: E402
from src.services.roster_update import RosterUpdateService  # noqa: E402
from src.services.agent_pipeline import AgentPipeline  # noqa: E402
from database.services import AlertService  # noqa: E402
from config.pipeline_config import PipelineConfig  # noqa: E402
from database.models.alert import Alert  # noqa: E402

class ProjectionAlertPipeline:
    """
    Main orchestrator for the projection risk alert pipeline.
    
    Coordinates the full workflow from fetching fixtures to
    pushing enriched projections back to BigQuery.
    """
    
    def __init__(self):
        """
        Initialize the pipeline.
        If no config is provided, use default values.
        Args:
            config: PipelineConfig object
        """
        self.config = PipelineConfig.from_file()
        if not self.config:
            raise ValueError("Config file not found")
        
        self.run_id = get_run_id()
        self.logger = get_logger()
        self.logger.pipeline_start()
            
        self.dry_run = self.config.dry_run
        self.leagues = self.config.leagues
        self.fixtures = self.config.fixtures
        self.push_all = self.config.push_all
        self.fixtures_only = self.config.fixtures_only
        self.verbose = self.config.verbose

        self.projections_service = ProjectionsService()
        self.roster_update_service = RosterUpdateService()
        self.agent_pipeline = AgentPipeline(self.run_id)
        self.logger.success("Projection Alert Pipeline Initialized")
    
    # =========================================================================
    # Step 1: Fetch Fixtures
    # =========================================================================
    
    def get_fixtures(self) -> list[dict]:
        """
        Fetch upcoming fixtures from BigQuery projections table.
        
        Returns:
            list[dict]: Fixtures with 'fixture' and 'match_time' keys
        """

        self.logger.section("📅 STEP 1: Fetching Fixtures")
        
        fixtures = self.projections_service.get_upcoming_fixtures()

        if self.leagues:
            fixtures = [
                f for f in fixtures 
                if any(league.lower() in f['league'].lower() for league in self.leagues)
            ]

        if self.fixtures:
            fixtures = [
                f for f in fixtures 
                if f['fixture'] in self.fixtures
            ]

        self.logger.pipeline_fixtures(fixtures)
        
        if not fixtures:
            return []
        
        return fixtures 
    
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
        self.logger.fixture_info("Running agent pipeline", fixture)
        
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
            self.logger.fixture_warning(f"Could not parse match_time '{match_time}': {e}", fixture)
            fixture_date = datetime.now()
        
        # Run the agent pipeline
        # Note: Dry run mode still runs agents (for testing), but skips BigQuery push
        try:
            alerts = self.agent_pipeline.run_and_save(fixture, fixture_date)
            print(f"   ✅ Generated {len(alerts)} alerts")
            return alerts
        except Exception as e:
            print(f"   ❌ Agent pipeline failed: {e}")
            raise e
    
    # =========================================================================
    # Step 6-7: Enrich and Push
    # =========================================================================
    
    def enrich_and_push_projections(
        self,
        fixtures: list[str],
        alerts: list[Alert],
        push_all: bool = True
    ) -> int:
        """
        Pull projections, match with alerts, and push enriched data.
        
        Args:
            fixtures: List of fixture strings to process
            push_all: If True, push all projections (default); if False, only those with alerts
            
        Returns:
            int: Number of enriched rows pushed to BigQuery
        """
        print("\n📊 Step 6-7: Enriching projections with alerts")
        
        if not fixtures:
            print("   ⚠️  No fixtures to process")
            return 0

        if not alerts:
            print("   ℹ️  No alerts found for run id {self.run_id}")
            return 0
        else:
            print(f"   Processing {len(alerts)} alerts for run id {self.run_id}")
        
        # Step 6b: Pull projections from BigQuery
        projections = self.projections_service.get_all_projections_for_fixtures(fixtures)
        
        if projections.empty:
            print("   ❌ No projections found in BigQuery for these fixtures")
            return 0
        
        # Step 6c: Enrich projections with alerts
        # Note: db_alerts have the same fields as PlayerAlert, so duck typing works
        enriched = self.projections_service.enrich_with_alerts(projections, alerts)
        
        # Step 6d: Filter to only alerted projections (unless push_all)
        if not push_all:
            enriched = self.projections_service.filter_alerted_projections(enriched)
        
        if enriched.empty:
            print("   ⚠️  No enriched projections to push")
            return 0
        
        # Step 7: Push to BigQuery (skip in dry run mode)
        if self.dry_run:
            print(f"\n🔒 DRY RUN: Would push {len(enriched)} rows to BigQuery")
            print(f"   Destination: {self.projections_service.dest_table_id}")
            print(f"   (Skipping actual BigQuery write)")
        else:
            self.projections_service.push_enriched_projections(enriched)
        
        return len(enriched)

    def run_enrichment_only(self, run_id: str) -> None:
        """
        Run only the enrichment step using alerts from a previous run.
        
        Args:
            run_id: The run_id to fetch alerts for
        """
        print(f"\n📊 Running enrichment for run_id: {run_id}")
        
        # Fetch alerts from database
        alert_service = AlertService(run_id=run_id)
        alerts = alert_service.get_alerts_by_run_id(run_id)
        
        if not alerts:
            print(f"❌ No alerts found for run_id: {run_id}")
            return
        
        print(f"   Found {len(alerts)} alerts")
        
        # Extract fixtures from alerts
        fixtures = self.get_fixtures()
        fixture_names = [f['fixture'] for f in fixtures]
        print(f"   Extracted {len(fixtures)} fixtures")
        
        # Run enrichment
        self.enrich_and_push_projections(fixture_names, alerts)
    
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
        
        # Step 1: Get fixtures
        if fixtures is None:
            fixtures = self.get_fixtures()
        
        if not fixtures:
            self.logger.error("No fixtures to process. Exiting.")
            return
        
        self.logger.section("PROCESSING FIXTURES")
        
        all_alerts = []
        for i, fixture_data in enumerate(fixtures, 1):
            fixture = fixture_data['fixture']
            match_time = fixture_data['match_time']
            
            # Removing roster update from pipeline TODO: Separate Logging for Roster Updates
            # # Step 2-3: Update rosters
            # await self.roster_update_service.update_fixture_rosters(fixture)
            
            # Step 4-5: Run agents
            alerts = self.run_agents_for_fixture(fixture, match_time)
            all_alerts.extend(alerts)
        
        # Step 6-7: Enrich and push
        print("\n" + "="*60)
        print("📊 ENRICHMENT & EXPORT")
        print("="*60)
        
        enriched_count = 0
        if not self.dry_run:
            # Extract fixture names for enrichment
            fixture_names = [f['fixture'] for f in fixtures]
            enriched_count = self.enrich_and_push_projections(fixture_names, all_alerts)
        else:
            print("\n🔒 Dry run - skipping BigQuery write")
        
        
        # print("\n" + "="*60)
        # print("✅ PIPELINE COMPLETE")
        # print(f"   Run ID: {self.run_id}")
        # print("="*60)
        # print(f"   Fixtures processed: {len(fixtures)}")
        # print(f"   Alerts generated: {len(all_alerts)}")
        # print(f"   Projections enriched: {enriched_count}")
        # print(f"   Duration: {duration:.1f} seconds")
        # print(f"   Finished: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    def run(self, fixtures: Optional[list[dict]] = None) -> None:
        """
        Execute the full pipeline (sync wrapper).
        
        Args:
            fixtures: Optional list of fixtures to process. If not provided,
                     fetches from BigQuery.
        """
        if self.fixtures_only:
            _ = self.get_fixtures()
        else:
            asyncio.run(self.run_async())


def main():
    """Entry point for running the pipeline."""
    import sys
    # Check for enrich-only mode
    if len(sys.argv) > 2 and sys.argv[1] == '--enrich-only':
        run_id = sys.argv[2]
        pipeline = ProjectionAlertPipeline()
        pipeline.run_enrichment_only(run_id)
    else:
        pipeline = ProjectionAlertPipeline()
        pipeline.run()


if __name__ == "__main__":
    main()

