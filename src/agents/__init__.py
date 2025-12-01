"""
Agents package - AI agents for player risk assessment.

Contains:
- Research Agent: Searches for player injury news
- Assessment Agent: Evaluates risk based on findings (future)
- Data models: Pydantic models for agent I/O
"""

from .research_agent import ResearchAgent
from .models import Source, InjuryResearchFindings, TeamContext

__all__ = ['ResearchAgent', 'Source', 'InjuryResearchFindings', 'TeamContext']

