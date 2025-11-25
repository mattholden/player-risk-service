"""
Database enums and types.

This module contains all enum types used across database models.
Centralizing enums here makes them easy to reuse and maintain.
"""

from enum import Enum as PyEnum


class RiskTag(PyEnum):
    """
    Player risk level classification.
    
    Values represent the current assessed risk level for a player
    based on recent news articles and LLM analysis.
    """
    NO_RISK = "no_risk"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"  # Default when no assessment available
