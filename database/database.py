"""
Database configuration and utilities.

This module provides database connection management, session handling,
and table creation utilities using SQLAlchemy.
"""

import os
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv
# Import Base and models to ensure they're registered
from database.models import Base

# Load environment variables
load_dotenv()


class DatabaseManager:
    """
    Manages database connections and sessions.
    
    This class provides a centralized way to manage database connections,
    create sessions, and initialize the database schema.
    """
    
    def __init__(self, database_url: str = None):
        """
        Initialize the database manager.
        
        Args:
            database_url: Optional database URL. If not provided, 
                         reads from DATABASE_URL environment variable.
                         
        Raises:
            ValueError: If no database URL is provided or found
        """
        self.database_url = database_url or os.getenv('DATABASE_URL')
        
        if not self.database_url:
            raise ValueError(
                "DATABASE_URL not found. Please set it in your .env file."
            )
        
        # Create engine
        self.engine = create_engine(
            self.database_url,
            echo=False,  # Set to True to see SQL queries
            pool_pre_ping=True,  # Verify connections before using them
            pool_size=5,  # Connection pool size
            max_overflow=10  # Max connections beyond pool_size
        )
        
        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
    
    def create_tables(self):
        """
        Create all tables defined in the models.
        
        This will create tables for all models that inherit from Base.
        Tables that already exist will not be modified.
        """
        Base.metadata.create_all(bind=self.engine)
        print("✅ Database tables created successfully!")
    
    def drop_tables(self):
        """
        Drop all tables defined in the models.
        
        WARNING: This will delete all data in the tables!
        """
        Base.metadata.drop_all(bind=self.engine)
        print("⚠️  All tables dropped!")
    
    def get_session(self) -> Session:
        """
        Get a new database session.
        
        Returns:
            Session: SQLAlchemy session object
            
        Note:
            Remember to close the session when done:
            session = db.get_session()
            try:
                # ... use session
            finally:
                session.close()
        """
        return self.SessionLocal()
    
    @contextmanager
    def session_scope(self):
        """
        Provide a transactional scope for database operations.
        
        This is a context manager that automatically handles commit/rollback
        and session cleanup.
        
        Usage:
            with db.session_scope() as session:
                session.add(article)
                # Automatically commits on success, rolls back on error
        
        Yields:
            Session: SQLAlchemy session object
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def health_check(self) -> bool:
        """
        Check if database connection is healthy.
        
        Returns:
            bool: True if connection is healthy, False otherwise
        """
        try:
            with self.session_scope() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            print(f"Database health check failed: {e}")
            return False


# Create a single database manager instance when module is imported
# This ensures connection pooling is shared across the application
db_manager = DatabaseManager()


def get_session() -> Session:
    """
    Convenience function to get a database session.
    
    Returns:
        Session: SQLAlchemy session object
        
    Example:
        from database import get_session
        
        session = get_session()
        try:
            # ... use session
        finally:
            session.close()
    """
    return db_manager.get_session()


def session_scope():
    """
    Convenience function for transactional scope.
    
    Returns:
        Context manager for database session
        
    Example:
        from database import session_scope
        
        with session_scope() as session:
            session.add(article)
            # Auto-commits on success, rolls back on error
    """
    return db_manager.session_scope()

