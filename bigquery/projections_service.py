"""
Projections service for enriching BigQuery projections with alert data.

This service handles:
- Pulling player projections from BigQuery
- Matching projections with pipeline-generated alerts
- Enriching projections with alert_level and alert_description
- Pushing enriched data to a dev table for review
"""

import os
from typing import Optional
from datetime import datetime
import pandas as pd

from bigquery.client import BigQueryClient
from bigquery.matching import PlayerMatcher
from src.agents.models import PlayerAlert
from database.enums import AlertLevel


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
        self.client = client or BigQueryClient()
        self.matcher = PlayerMatcher()
        
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
        fixtures_str = ", ".join([f"'{f}'" for f in fixtures])
        query = f"""
            SELECT * 
            FROM `{self.source_table_id}`
            WHERE {fixture_column} IN ({fixtures_str})
        """
        
        print(f"📊 Fetching projections for {len(fixtures)} fixtures...")
        df = self.client.query(query)
        print(f"   Found {len(df)} total projection rows")
        
        return df
    
    def enrich_with_alerts(
        self,
        projections: pd.DataFrame,
        alerts: list[PlayerAlert],
        player_name_column: str = "player_name",
        fixture_column: str = "fixture"
    ) -> pd.DataFrame:
        """
        Enrich projections DataFrame with alert information.
        
        Matches alerts to projections by player name (with fuzzy matching)
        and fixture, then adds alert_level and alert_description columns.
        
        Args:
            projections: DataFrame of projections from BigQuery
            alerts: List of PlayerAlert objects from the pipeline
            player_name_column: Column name for player names in projections
            fixture_column: Column name for fixture in projections
            
        Returns:
            pd.DataFrame: Enriched projections with alert columns
        """
        if projections.empty:
            print("⚠️ No projections to enrich")
            return projections
        
        if not alerts:
            print("⚠️ No alerts to match - returning projections with empty alert columns")
            projections = projections.copy()
            projections["alert_level"] = AlertLevel.NO_ALERT.value
            projections["alert_description"] = None
            return projections
        
        print(f"\n🔍 Matching {len(alerts)} alerts to {len(projections)} projections...")
        
        # Create a copy to avoid modifying original
        enriched = projections.copy()
        
        # Initialize alert columns
        enriched["alert_level"] = AlertLevel.NO_ALERT.value
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
                    break
        
        print(f"   ✅ Matched {matched_count} projections with alerts")
        print(f"   ℹ️  {len(enriched) - matched_count} projections have no matching alerts")
        
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
            include_no_alert: If True, include rows with NO_ALERT level
            
        Returns:
            pd.DataFrame: Filtered projections
        """
        if include_no_alert:
            return enriched_projections
        
        # Filter to only matched alerts (excluding NO_ALERT)
        filtered = enriched_projections[
            enriched_projections["alert_level"] != AlertLevel.NO_ALERT.value
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
            print("⚠️ No data to push to BigQuery")
            return
        
        # Add metadata columns
        enriched_projections = enriched_projections.copy()
        enriched_projections["enriched_at"] = datetime.utcnow()
        
        # Remove temporary matching column if present
        if "alert_matched" in enriched_projections.columns:
            enriched_projections = enriched_projections.drop(columns=["alert_matched"])
        
        print(f"\n📤 Pushing {len(enriched_projections)} rows to {self.dest_table_id}...")
        
        self.client.write_dataframe(
            enriched_projections,
            self.dest_table_id,
            write_disposition=write_disposition
        )
    
    def run_enrichment_pipeline(
        self,
        alerts: list[PlayerAlert],
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
            alerts: List of PlayerAlert objects from the pipeline
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

