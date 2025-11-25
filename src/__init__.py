"""
Main application package for Player Risk Service.

This is the core backend service providing:
- REST API endpoints (FastAPI)
- Business logic and services
- External API integrations (NewsAPI, LLM)
- Background job processing

The API can be consumed by:
- Internal Streamlit dashboard (streamlit_app/)
- Other services in the company
- Third-party integrations
"""

__version__ = "0.1.0"
