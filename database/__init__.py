"""
Database package.

This package contains all database-related code:
- models: SQLAlchemy ORM models
- database: Connection management and sessions
- repositories: Data access layer (future)
"""

# Import and expose key components
from database.base import Base
from database.models import Article, Player, RiskTag
from database.database import (
    DatabaseManager,
    db_manager,
    get_session,
    session_scope
)

__all__ = [
    'Base',
    'Article',
    'Player',
    'RiskTag',
    'DatabaseManager',
    'db_manager',
    'get_session',
    'session_scope',
]

