"""
Database enums and types.

This module contains all enum types used across database models.
Centralizing enums here makes them easy to reuse and maintain.
"""

from enum import Enum as PyEnum


class AlertLevel(PyEnum):
    """
    Player alert level classification.
    
    Values represent the current assessed alert level for a player
    based on recent news articles and LLM analysis.
    """
    NO_ALERT = "no_alert"
    LOW_ALERT = "low"
    MEDIUM_ALERT = "medium"
    HIGH_ALERT = "high"
