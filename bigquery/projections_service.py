"""
Projections service for enriching BigQuery projections with alert data.

This service handles:
- Pulling player projections from BigQuery
- Matching projections with pipeline-generated alerts
- Enriching projections with alert_level and alert_description
- Pushing enriched data to a dev table for review
"""

import os
from typing import Optional, Union, List
from datetime import datetime, timezone
import pandas as pd

from bigquery.client import BigQueryClient
from src.utils.matching import PlayerMatcher
from src.agents.models import PlayerAlert
from database.models.alert import Alert
from src.logging import get_logger
# Type alias for alert objects - accepts either pydantic model or database model
AlertLike = Union[PlayerAlert, Alert]


class ProjectionsService:
    """
    Service for managing player projections and alert enrichment.
    
    Pulls projections from BigQuery, matches them with alerts from
    the agentic pipeline, and pushes enriched data back to BigQuery.
    
    Usage:
        service = ProjectionsService()
        projections = service.get_projections_for_fixture("Arsenal vs Brentford")
        enriched = service.enrich_with_alerts(projections, alerts)
        service.push_enriched_projections(enriched)
    """
    
    def __init__(
        self,
        client: Optional[BigQueryClient] = None,
        source_dataset: Optional[str] = None,
        source_table: Optional[str] = None,
        dest_dataset: Optional[str] = None,
        dest_table: Optional[str] = None
    ):
        """
        Initialize the ProjectionsService.
        
        Args:
            client: BigQuery client instance (creates one if not provided)
            source_dataset: Dataset containing projections (env: BIGQUERY_SOURCE_DATASET)
            source_table: Table containing projections (env: BIGQUERY_SOURCE_TABLE)
            dest_dataset: Dataset for enriched output (env: BIGQUERY_DEST_DATASET)
            dest_table: Table for enriched output (env: BIGQUERY_DEST_TABLE)
        """
        self.today = datetime.now().strftime('%Y-%m-%d')
        self.specific_date = datetime(2025,1,14,12,0,0)
        self.client = client or BigQueryClient()
        self.matcher = PlayerMatcher()
        self.logger = get_logger()
        # Source table configuration
        self.source_dataset = source_dataset or os.getenv("BIGQUERY_SOURCE_DATASET")
        self.source_table = source_table or os.getenv("BIGQUERY_SOURCE_TABLE")
        
        # Destination table configuration  
        self.dest_dataset = dest_dataset or os.getenv("BIGQUERY_DEST_DATASET")
        self.dest_table = dest_table or os.getenv("BIGQUERY_DEST_TABLE", "projections_with_alerts_dev")
        
        # Build fully qualified table IDs
        project_id = self.client.project_id
        self.source_table_id = f"{project_id}.{self.source_dataset}.{self.source_table}"
        self.dest_table_id = f"{project_id}.{self.dest_dataset}.{self.dest_table}"

        self.logger.success("Projections Service Initialized")
    
    def get_upcoming_fixtures(
        self,
        fixture_column: str = "fixture",
        match_time_column: str = "match_time",
        league_column: str = "season_name"
    ) -> list[dict]:
        """
        Get distinct upcoming fixtures from the projections table.
        
        Returns fixtures with their match times and leagues, useful for determining
        which fixtures to process through the agent pipeline.
        
        Args:
            fixture_column: Column name for fixture in source table
            match_time_column: Column name for match time in source table
            league_column: Column name for league/season in source table
            
        Returns:
            list[dict]: List of fixtures with keys 'fixture', 'match_time', 'league'
                Example: [
                    {'fixture': 'Arsenal vs Brentford', 'match_time': '2025-12-03 19:45:00', 'league': 'Premier League'},
                    {'fixture': 'Liverpool vs Brighton', 'match_time': '2025-12-04 20:00:00', 'league': 'Premier League'}
                ]
        """
        
        query = f"""
            SELECT DISTINCT 
                {fixture_column} as fixture,
                {match_time_column} as match_time,
                {league_column} as league
            FROM `{self.source_table_id}`
            WHERE {match_time_column} > '{self.specific_date}'
            ORDER BY {match_time_column}
        """
        
        df = self.client.query(query)
        fixtures = df.to_dict(orient="records")
        
        return fixtures
    
    def get_projections(
        self,
        fixture: Optional[str] = None,
        fixture_date: Optional[datetime] = None,
        player_name_column: str = "player_name",
        fixture_column: str = "fixture"
    ) -> pd.DataFrame:
        """
        Pull projections from BigQuery.
        
        Args:
            fixture: Optional fixture filter (e.g., "Arsenal vs Brentford")
            fixture_date: Optional date filter
            player_name_column: Column name for player names in source table
            fixture_column: Column name for fixture in source table
            
        Returns:
            pd.DataFrame: Projections data
        """
        # Build query with optional filters
        query = f"SELECT * FROM `{self.source_table_id}`"
        
        conditions = []
        if fixture:
            # Handle fixture matching (could be exact or partial)
            conditions.append(f"{fixture_column} = '{fixture}'")
        if fixture_date:
            date_str = fixture_date.strftime("%Y-%m-%d")
            conditions.append(f"DATE(fixture_date) = '{date_str}'")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        print("📊 Fetching projections from BigQuery...")
        print(f"   Query: {query}")
        
        df = self.client.query(query)
        print(f"   Found {len(df)} projection rows")
        
        return df
    
    def get_all_projections_for_fixtures(
        self,
        fixtures: list[str],
        player_name_column: str = "player_name",
        fixture_column: str = "fixture"
    ) -> pd.DataFrame:
        """
        Pull projections for multiple fixtures.
        
        Args:
            fixtures: List of fixture strings
            player_name_column: Column name for player names
            fixture_column: Column name for fixture
            
        Returns:
            pd.DataFrame: Combined projections for all fixtures
        """
        if not fixtures:
            return pd.DataFrame()
        
        # Build IN clause for fixtures
        fixtures_str = ", ".join([self._escape_quotes(f) for f in fixtures])
        print(f"DEBUG fixtures_str: {fixtures_str}") #######
        query = f"""
            SELECT * 
            FROM `{self.source_table_id}`
            WHERE {fixture_column} IN ({fixtures_str})
            AND match_time > '{self.today}'
        """
        print(f"DEBUG full query:\n{query}")  # Add this
        
        print(f"📊 Fetching projections for {len(fixtures)} fixtures...")
        df = self.client.query(query)
        print(f"   Found {len(df)} total projection rows")
        
        return df
    
    def enrich_with_alerts(
        self,
        projections: pd.DataFrame,
        alerts: List[AlertLike],
        player_name_column: str = "player_name",
        fixture_column: str = "fixture"
    ) -> pd.DataFrame:
        """
        Enrich projections DataFrame with alert information.
        
        Matches alerts to projections by player name (with fuzzy matching)
        and fixture, then adds alert_level and alert_description columns.
        
        Args:
            projections: DataFrame of projections from BigQuery
            alerts: List of alert objects (PlayerAlert or database Alert)
            player_name_column: Column name for player names in projections
            fixture_column: Column name for fixture in projections
            
        Returns:
            pd.DataFrame: Enriched projections with alert columns
        """
        if projections.empty:
            self.logger.warning("No projections to enrich")
            return projections
        
        if not alerts:
            self.logger.warning("No alerts to match - returning projections with null alert columns")
            projections = projections.copy()
            projections["alert_level"] = None
            projections["alert_description"] = None
            return projections
        
        self.logger.info(f"Matching {len(alerts)} alerts to {len(projections)} projections...")
        
        # Create a copy to avoid modifying original
        enriched = projections.copy()
        
        # Initialize alert columns with null (no alert = healthy player)
        enriched["alert_level"] = None
        enriched["alert_description"] = None
        enriched["alert_matched"] = False
        
        # Build lookup for faster matching
        alerts_by_fixture: dict[str, list[PlayerAlert]] = {}
        for alert in alerts:
            fixture_key = alert.fixture.lower().strip()
            if fixture_key not in alerts_by_fixture:
                alerts_by_fixture[fixture_key] = []
            alerts_by_fixture[fixture_key].append(alert)
        
        # Match each projection row
        matched_count = 0
        for idx, row in enriched.iterrows():
            projection_player = row[player_name_column]
            projection_fixture = row[fixture_column].lower().strip()
            
            # Get alerts for this fixture
            fixture_alerts = alerts_by_fixture.get(projection_fixture, [])
            
            # Try to match player
            for alert in fixture_alerts:
                if self.matcher.is_match(projection_player, alert.player_name):
                    enriched.at[idx, "alert_level"] = alert.alert_level.value
                    enriched.at[idx, "alert_description"] = alert.description
                    enriched.at[idx, "alert_matched"] = True
                    matched_count += 1
                    alerts_by_fixture[projection_fixture].remove(alert)
                    self.logger.alert_matched(alert, projection_player, projection_fixture)
                    break
        unmatched_count = len(alerts) - matched_count
        self.logger.alert_matching_summary(matched_count, unmatched_count)
        self.logger.alerts_not_matched(alerts_by_fixture)
        
        return enriched
    
    def filter_alerted_projections(
        self,
        enriched_projections: pd.DataFrame,
        include_no_alert: bool = False
    ) -> pd.DataFrame:
        """
        Filter to only projections that have alerts.
        
        Args:
            enriched_projections: DataFrame with alert columns
            include_no_alert: If True, include rows with null alert_level
            
        Returns:
            pd.DataFrame: Filtered projections
        """
        if include_no_alert:
            return enriched_projections
        
        # Filter to only matched alerts (excluding null/None)
        filtered = enriched_projections[
            enriched_projections["alert_level"].notna()
        ]
        
        print(f"   Filtered to {len(filtered)} projections with active alerts")
        return filtered
    
    def push_enriched_projections(
        self,
        enriched_projections: pd.DataFrame,
        write_disposition: str = "WRITE_APPEND"
    ) -> None:
        """
        Push enriched projections to the destination BigQuery table.
        
        Args:
            enriched_projections: DataFrame with alert columns added
            write_disposition: How to handle existing data
                - WRITE_TRUNCATE: Replace entire table
                - WRITE_APPEND: Append new rows
        """
        if enriched_projections.empty:
            self.logger.error("No data to push to BigQuery")
            return
        
        # Add metadata columns
        enriched_projections = enriched_projections.copy()
        enriched_projections["enriched_at"] = datetime.now(timezone.utc)
        
        # Remove temporary matching column if present
        if "alert_matched" in enriched_projections.columns:
            enriched_projections = enriched_projections.drop(columns=["alert_matched"])
        
        self.logger.info(f"Pushing {len(enriched_projections)} rows to {self.dest_table_id}...")
        
        self.client.write_dataframe(
            enriched_projections,
            self.dest_table_id,
            write_disposition=write_disposition
        )
    
    def run_enrichment_pipeline(
        self,
        alerts: List[AlertLike],
        fixtures: Optional[list[str]] = None,
        player_name_column: str = "player_name",
        fixture_column: str = "fixture",
        push_all: bool = False,
        write_disposition: str = "WRITE_APPEND"
    ) -> pd.DataFrame:
        """
        Run the full enrichment pipeline.
        
        Convenience method that:
        1. Pulls projections from BigQuery
        2. Enriches with alerts
        3. Optionally filters to only alerted projections
        4. Pushes to destination table
        
        Args:
            alerts: List of alert objects (PlayerAlert or database Alert)
            fixtures: Optional list of fixtures to filter (infers from alerts if not provided)
            player_name_column: Column name for player names
            fixture_column: Column name for fixture
            push_all: If True, push all projections; if False, only push alerted ones
            write_disposition: How to handle existing data in dest table
            
        Returns:
            pd.DataFrame: The enriched (and optionally filtered) projections
        """
        # Infer fixtures from alerts if not provided
        if fixtures is None:
            fixtures = list(set(alert.fixture for alert in alerts))
        
        print(f"\n{'='*60}")
        print("🚀 Starting Projections Enrichment Pipeline")
        print(f"{'='*60}")
        print(f"   Fixtures: {fixtures}")
        print(f"   Alerts: {len(alerts)}")
        
        # Step 1: Pull projections
        projections = self.get_all_projections_for_fixtures(
            fixtures,
            player_name_column=player_name_column,
            fixture_column=fixture_column
        )
        
        if projections.empty:
            print("❌ No projections found for the specified fixtures")
            return projections
        
        # Step 2: Enrich with alerts
        enriched = self.enrich_with_alerts(
            projections,
            alerts,
            player_name_column=player_name_column,
            fixture_column=fixture_column
        )
        
        # Step 3: Optionally filter
        if not push_all:
            enriched = self.filter_alerted_projections(enriched)
        
        # Step 4: Push to BigQuery
        self.push_enriched_projections(enriched, write_disposition=write_disposition)
        
        print(f"\n{'='*60}")
        print("✅ Enrichment Pipeline Complete")
        print(f"{'='*60}")
        
        return enriched

    def _escape_quotes(self, s: str) -> str:
        """Escape single quotes for SQL strings and wrap in quotes."""
        # Use backslash escaping instead of doubled quotes
        escaped = s.replace("\\", "\\\\").replace("'", "\\'")
        return f"'{escaped}'"

