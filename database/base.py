"""
Base class for all SQLAlchemy models.

This module provides the declarative base that all models inherit from.
Import this base in all model files to ensure they share the same metadata.
"""

from sqlalchemy.ext.declarative import declarative_base

# Single declarative base for all models
# All models must inherit from this to share the same metadata
Base = declarative_base()

