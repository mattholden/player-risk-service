"""
Database initialization script.

This script creates all database tables defined in models.py.
Run this script to set up your database schema.

Usage:
    python init_db.py
"""

import sys
from database import DatabaseManager


def init_database():
    """Initialize the database by creating all tables."""
    print("="*60)
    print("Database Initialization")
    print("="*60 + "\n")
    
    try:
        # Initialize database manager
        print("Connecting to database...")
        db = DatabaseManager()
        
        # Test connection
        if not db.health_check():
            print("❌ Database connection failed!")
            print("\nPlease check:")
            print("1. Docker container is running: docker-compose ps")
            print("2. DATABASE_URL in .env is correct")
            sys.exit(1)
        
        print("✅ Database connection successful!\n")
        
        # Create tables
        print("Creating database tables...")
        db.create_tables()
        
        print("\n" + "="*60)
        print("Database initialized successfully! ✅")
        print("="*60)
        print("\nTables created:")
        print("  - articles")
        
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print("\nMake sure your .env file contains:")
        print("DATABASE_URL=postgresql://user:password@localhost:5434/player_risk_db")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        sys.exit(1)


def reset_database():
    """
    Reset the database by dropping and recreating all tables.
    
    WARNING: This will delete all data!
    """
    print("="*60)
    print("⚠️  DATABASE RESET WARNING ⚠️")
    print("="*60)
    print("\nThis will DELETE ALL DATA in your database!")
    print("Are you sure you want to continue? (yes/no): ", end="")
    
    confirmation = input().strip().lower()
    
    if confirmation != 'yes':
        print("Reset cancelled.")
        return
    
    print("\n" + "="*60)
    print("Resetting Database")
    print("="*60 + "\n")
    
    try:
        db = DatabaseManager()
        
        print("Dropping all tables...")
        db.drop_tables()
        
        print("\nCreating fresh tables...")
        db.create_tables()
        
        print("\n" + "="*60)
        print("Database reset complete! ✅")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Error resetting database: {e}")
        sys.exit(1)


def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        reset_database()
    else:
        init_database()


if __name__ == "__main__":
    main()

