"""
BigQuery module for player projections integration.

This module handles:
- Pulling projections from BigQuery
- Enriching projections with alert data
- Pushing enriched data back to BigQuery dev tables
"""

from bigquery.client import BigQueryClient
from bigquery.projections_service import ProjectionsService

__all__ = [
    "BigQueryClient",
    "ProjectionsService",
]

