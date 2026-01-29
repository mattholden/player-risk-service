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
from prompts import get_sport_config  # noqa: E402
from src.utils.date_extraction import parse_date_string  # noqa: E402
from src.agents.models import AgentData  # noqa: E402
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
        
        # Load sport-specific prompts
        self.sport = self.config.sport
        self.dry_run = self.config.dry_run
        self.leagues = self.config.leagues
        self.fixtures = self.config.fixtures
        self.push_all = self.config.push_all
        self.fixtures_only = self.config.fixtures_only
        self.verbose = self.config.verbose

        self.projections_service = ProjectionsService()
        self.roster_update_service = RosterUpdateService()
        self.agent_pipeline = AgentPipeline(self.run_id, self.sport)
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
    
    def run_agents_for_fixture(self, agent_data: AgentData, max_retries: int = 3) -> list:
        """
        Run the agentic pipeline for a fixture and save alerts with retry logic.
        
        Implements a retry mechanism that:
        - Retries up to max_retries times on failure
        - Checks if alerts were saved before retrying (to avoid duplicates)
        - Gracefully continues to next fixture if all retries exhausted
        
        Args:
            agent_data: AgentData object
            max_retries: Maximum number of retry attempts (default: 3)
            
        Returns:
            list: Generated PlayerAlert objects (empty list if all retries fail)
        """
        self.logger.fixture_info("Running agent pipeline", agent_data.fixture)
        
        # Run the agent pipeline with retry logic
        # Note: Dry run mode still runs agents (for testing), but skips BigQuery push
        for attempt in range(1, max_retries + 1):
            try:
                alerts = self.agent_pipeline.run_and_save(agent_data)
                return alerts
            except Exception as e:
                # Check if alerts were written to DB despite the error
                # This can happen if the error occurred after save_alerts()
                if self.agent_pipeline.alert_service.alerts_exist_for_fixture(agent_data.fixture):
                    self.logger.warning(
                        f"Fixture {agent_data.fixture} had error but alerts were saved. "
                        f"Retrieving saved alerts."
                    )
                    return self.agent_pipeline.alert_service.get_alerts_for_fixture_and_run(
                        agent_data.fixture
                    )
                
                # Log the failure
                if attempt < max_retries:
                    self.logger.warning(
                        f"Attempt {attempt}/{max_retries} failed for {agent_data.fixture}: {e}. "
                        f"Retrying..."
                    )
                else:
                    self.logger.error(
                        f"Fixture {agent_data.fixture} failed after {max_retries} attempts: {e}. "
                        f"Moving to next fixture."
                    )
        
        # All retries exhausted - return empty list to continue pipeline
        return []
    
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
        
        if not fixtures:
            self.logger.warning("No fixtures to process")
            return 0

        if not alerts:
            self.logger.warning(f"No alerts found for run id {self.run_id}")
            return 0
        else:
            self.logger.info(f"Processing {len(alerts)} alerts for run id {self.run_id}")
        
        # Step 6b: Pull projections from BigQuery
        projections = self.projections_service.get_all_projections_for_fixtures(fixtures)
        
        if projections.empty:
            self.logger.error("No projections found in BigQuery for these fixtures")
            return 0
        
        # Step 6c: Enrich projections with alerts
        # Note: db_alerts have the same fields as PlayerAlert, so duck typing works
        enriched = self.projections_service.enrich_with_alerts(projections, alerts)
        
        # Step 6d: Filter to only alerted projections (unless push_all)
        if not push_all:
            enriched = self.projections_service.filter_alerted_projections(enriched)
        
        if enriched.empty:
            self.logger.error("No enriched projections to push - **This should not happen**")
            return 0
        
        self.projections_service.push_enriched_projections(enriched)
        

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
        self.logger.pipeline_complete(fixtures, alerts)
    
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
            agent_data = AgentData(
                fixture=fixture_data['fixture'],
                match_time=parse_date_string(fixture_data['match_time'])
            )
            
            # Removing roster update from pipeline TODO: Separate Logging for Roster Updates
            # # Step 2-3: Update rosters
            # await self.roster_update_service.update_fixture_rosters(fixture)
            
            # Step 4-5: Run agents
            alerts = self.run_agents_for_fixture(agent_data)
            all_alerts.extend(alerts)
        
        # Step 6-7: Enrich and push
        self.logger.section("📊 PROJECTIONS MERGE WITH ALERTS & EXPORT TO BIGQUERY")
        
        if not self.dry_run:
            # Extract fixture names for enrichment
            fixture_names = [f['fixture'] for f in fixtures]
            self.enrich_and_push_projections(fixture_names, all_alerts)
        else:
            self.logger.dry_run()
        
        self.logger.pipeline_complete(fixtures, all_alerts)
    
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

