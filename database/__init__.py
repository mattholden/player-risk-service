"""
Database package.

This package contains all database-related code:
- models: SQLAlchemy ORM models
- database: Connection management and sessions
- repositories: Data access layer (future)
"""

# Import and expose key components
from database.base import Base
from database.models import Article, Player, Alert
from database.enums import AlertLevel
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
    'Alert',
    'AlertLevel',
    'DatabaseManager',
    'db_manager',
    'get_session',
    'session_scope',
]

