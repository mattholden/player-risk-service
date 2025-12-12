"""
BigQuery client for managing connections and queries.

Provides a clean interface for interacting with BigQuery,
with proper authentication and connection handling.
"""

import os
from typing import Optional
from google.cloud import bigquery
from google.oauth2 import service_account
import pandas as pd


class BigQueryClient:
    """
    Client for interacting with Google BigQuery.
    
    Handles authentication, connection management, and provides
    methods for common operations like queries and table writes.
    
    Usage:
        client = BigQueryClient()
        df = client.query("SELECT * FROM `project.dataset.table`")
        client.write_dataframe(df, "project.dataset.new_table")
    """
    
    def __init__(
        self,
        project_id: Optional[str] = None,
        credentials_path: Optional[str] = None
    ):
        """
        Initialize the BigQuery client.
        
        Args:
            project_id: GCP project ID (defaults to BIGQUERY_PROJECT_ID env var)
            credentials_path: Path to service account JSON (defaults to GOOGLE_APPLICATION_CREDENTIALS env var)
        """
        self.project_id = project_id or os.getenv("BIGQUERY_PROJECT_ID")
        self.credentials_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        
        if not self.project_id:
            raise ValueError(
                "BigQuery project ID is required. "
                "Set BIGQUERY_PROJECT_ID environment variable or pass project_id parameter."
            )
        
        self._client: Optional[bigquery.Client] = None
    
    @property
    def client(self) -> bigquery.Client:
        """
        Lazy initialization of BigQuery client.
        
        Returns:
            bigquery.Client: Authenticated BigQuery client
        """
        if self._client is None:
            self._client = self._create_client()
        return self._client
    
    def _create_client(self) -> bigquery.Client:
        """
        Create and authenticate a BigQuery client.
        
        Returns:
            bigquery.Client: Authenticated client
        """
        if self.credentials_path:
            # Use explicit service account credentials
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=["https://www.googleapis.com/auth/bigquery"]
            )
            return bigquery.Client(
                project=self.project_id,
                credentials=credentials
            )
        else:
            # Use Application Default Credentials (ADC)
            # This works with: gcloud auth application-default login
            return bigquery.Client(project=self.project_id)
    
    def query(self, sql: str) -> pd.DataFrame:
        """
        Execute a SQL query and return results as a DataFrame.
        
        Args:
            sql: SQL query string
            
        Returns:
            pd.DataFrame: Query results
        """
        query_job = self.client.query(sql)
        return query_job.to_dataframe()
    
    def query_to_list(self, sql: str) -> list[dict]:
        """
        Execute a SQL query and return results as a list of dictionaries.
        
        Args:
            sql: SQL query string
            
        Returns:
            list[dict]: Query results as list of row dictionaries
        """
        df = self.query(sql)
        return df.to_dict(orient="records")
    
    def write_dataframe(
        self,
        df: pd.DataFrame,
        table_id: str,
        write_disposition: str = "WRITE_TRUNCATE",
        schema: Optional[list] = None
    ) -> None:
        """
        Write a DataFrame to a BigQuery table.
        
        Args:
            df: DataFrame to write
            table_id: Fully qualified table ID (project.dataset.table)
            write_disposition: How to handle existing data
                - WRITE_TRUNCATE: Overwrite table
                - WRITE_APPEND: Append to table
                - WRITE_EMPTY: Fail if table exists
            schema: Optional explicit schema (list of bigquery.SchemaField)
        """
        job_config = bigquery.LoadJobConfig(
            write_disposition=write_disposition,
        )
        
        if schema:
            job_config.schema = schema
        
        job = self.client.load_table_from_dataframe(
            df,
            table_id,
            job_config=job_config
        )
        
        # Wait for the job to complete
        job.result()
        
        print(f"✅ Wrote {len(df)} rows to {table_id}")
    
    def table_exists(self, table_id: str) -> bool:
        """
        Check if a table exists in BigQuery.
        
        Args:
            table_id: Fully qualified table ID (project.dataset.table)
            
        Returns:
            bool: True if table exists
        """
        try:
            self.client.get_table(table_id)
            return True
        except Exception:
            return False
    
    def get_table_schema(self, table_id: str) -> list:
        """
        Get the schema of a BigQuery table.
        
        Args:
            table_id: Fully qualified table ID
            
        Returns:
            list: List of SchemaField objects
        """
        table = self.client.get_table(table_id)
        return list(table.schema)
    
    def health_check(self) -> bool:
        """
        Verify BigQuery connection is working.
        
        Returns:
            bool: True if connection is healthy
        """
        try:
            # Run a simple query to verify connectivity
            self.client.query("SELECT 1").result()
            return True
        except Exception as e:
            print(f"BigQuery health check failed: {e}")
            return False

