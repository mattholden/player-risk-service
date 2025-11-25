"""
Database models package.

This module imports and exposes all database models.
Importing this package ensures all models are registered with the Base metadata.
"""

from database.base import Base
from database.models.article import Article

# Export Base and all models
__all__ = ['Base', 'Article']

