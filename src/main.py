"""
Main backend application entry point.

This is the core API service that:
1. Provides REST API endpoints for player risk data
2. Runs background jobs for article collection and analysis
3. Can be consumed by Streamlit UI or other services

Future: Will use FastAPI for REST endpoints
"""

import time
import sys
from database import db_manager


def main():
    """Main entry point for backend API service."""
    print("="*60)
    print("Player Risk Service - API Backend")
    print("="*60)
    
    # Check database connection
    print("\nChecking database connection...")
    if not db_manager.health_check():
        print("❌ Database connection failed!")
        print("Please check DATABASE_URL and ensure postgres is running.")
        sys.exit(1)
    
    print("✅ Database connection healthy!")
    
    # TODO: Start FastAPI server here
    # from src.api.main import app
    # import uvicorn
    # uvicorn.run(app, host="0.0.0.0", port=8000)
    
    # For now, keep container running
    print("\n" + "="*60)
    print("API Backend is running...")
    print("Future: FastAPI server will run here")
    print("Press Ctrl+C to stop.")
    print("="*60)
    
    try:
        while True:
            time.sleep(60)
            # Future: Background jobs run here
            # - Fetch articles periodically
            # - Analyze risks
            # - Update player statuses
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")


if __name__ == "__main__":
    main()
