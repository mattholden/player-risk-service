"""
Test script to verify PostgreSQL database connection.

This script tests the connection to the PostgreSQL database
using SQLAlchemy. It should be run after the database container
is started via docker-compose.
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_database_connection():
    """
    Test the connection to the PostgreSQL database.
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ ERROR: DATABASE_URL not found in environment variables")
        print("\nMake sure your .env file contains:")
        print("DATABASE_URL=postgresql://postgres:your_password@localhost:5434/player_risk_db")
        return False
    
    print(f"Attempting to connect to database...")
    print(f"Connection string: {database_url.replace(database_url.split(':')[2].split('@')[0], '****')}")
    
    try:
        # Create engine
        engine = create_engine(database_url, echo=False)
        
        # Test connection with a simple query
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            
            print("\n✅ SUCCESS: Connected to PostgreSQL!")
            print(f"PostgreSQL version: {version}\n")
            
            # Get database name
            result = connection.execute(text("SELECT current_database();"))
            db_name = result.fetchone()[0]
            print(f"Connected to database: {db_name}")
            
            # Check if we can create tables (test permissions)
            result = connection.execute(text("SELECT current_user;"))
            user = result.fetchone()[0]
            print(f"Connected as user: {user}")
            
            print("\n✅ Database is ready for use!")
            return True
            
    except Exception as e:
        print(f"\n❌ ERROR: Failed to connect to database")
        print(f"Error details: {str(e)}")
        print("\nTroubleshooting:")
        print("1. Check that Docker container is running: docker-compose ps")
        print("2. Verify DATABASE_URL in .env matches your docker-compose.yml settings")
        print("3. Ensure port 5434 is accessible and not blocked")
        return False


def main():
    """Main function to run the database connection test."""
    print("="*60)
    print("PostgreSQL Database Connection Test")
    print("="*60 + "\n")
    
    success = test_database_connection()
    
    print("\n" + "="*60)
    if success:
        print("Test completed successfully! ✅")
        print("\nYou can now:")
        print("- Create SQLAlchemy models")
        print("- Set up database tables")
        print("- Start storing articles")
    else:
        print("Test failed ❌")
        print("Please fix the issues above and try again.")
    print("="*60)


if __name__ == "__main__":
    main()

