"""
Database package.

This package contains all database-related code:
- models: SQLAlchemy ORM models
- database: Connection management and sessions
- services: Business logic for database operations
"""

# Import and expose key components
from database.base import Base
from database.models import Article, Player, Alert, Roster, Team
from database.enums import AlertLevel
from database.database import (
    DatabaseManager,
    db_manager,
    get_session,
    session_scope
)
from database.services import AlertService

__all__ = [
    'Base',
    'Article',
    'Player',
    'Alert',
    'Roster',
    'Team',
    'AlertLevel',
    'AlertService',
    'DatabaseManager',
    'db_manager',
    'get_session',
    'session_scope',
]

