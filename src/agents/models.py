"""
Pydantic data models for agent inputs and outputs.

These models provide type validation, serialization, and clear contracts
between different parts of the agent pipeline.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class PlayerContext(BaseModel):
    """
    Input context for researching a player's injury status.
    
    This is what we pass to the Research Agent to begin the search.
    """
    name: str = Field(..., description="Player's full name")
    fixture: str = Field(..., description="Match fixture (e.g., 'Oxford United vs Ipswich Town')")
    fixture_date: datetime = Field(..., description="Date and time of the fixture")
    team: Optional[str] = Field(None, description="Player's team")
    position: Optional[str] = Field(None, description="Player's position (e.g., 'Forward', 'Defender')")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Jack Currie",
                "fixture": "Oxford United vs Ipswich Town",
                "fixture_date": "2025-11-28T19:45:00",
                "team": "Oxford United",
                "position": "Defender"
            }
        }

class TeamContext(BaseModel):
    """
    Input context for researching a team's injury status.
    """
    team: str = Field(..., description="Team name")
    fixture: str = Field(..., description="Match fixture (e.g., 'Arsenal vs Brentford')")
    fixture_date: datetime = Field(..., description="Date and time of the fixture")
    
    class Config:
        json_schema_extra = {
            "example": {
                "team": "Arsenal",
                "fixture": "Arsenal vs Brentford",
                "fixture_date": "2025-11-28T19:45:00"
            }
        }

class Source(BaseModel):
    """
    A single source citation found during research.
    
    This could be a tweet, news article, official team report, etc.
    """
    url: str = Field(..., description="URL to the source")
    title: str = Field(..., description="Title or headline of the source")
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://twitter.com/OxfordUnited/status/123456",
                "title": "Oxford United Official",
            }
        }

class InjuryResearchFindings(BaseModel):

    team_name: str = Field(..., description = "Team being researched")
    fixture: str = Field(..., description = "Match fixture (e.g., 'Arsenal vs Brentford')")
    findings: List[str] = Field(
        default_factory=list, 
        description = "List of findings"
        )
    sources: List[Source] = Field(
        default_factory=list, 
        description = "List of sources"
        )
    confidence_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence in findings (0.0 = no info, 1.0 = very confident)"
        )
    search_timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When this research was conducted"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "team_name": "Arsenal",
                "fixture": "Arsenal vs Brentford",
                "findings": [
                    "Player X is injured and will be out for the next 2 weeks",
                    "Player Y is doubtful for the next match",
                    "Player Z is available for the next match"
                ],
                "sources": [
                    {
                        "url": "https://twitter.com/Arsenal/status/123456",
                        "title": "Arsenal Official",
                    }
                ],
                "confidence_score": 0.85,
            }
        }
class ResearchFindings(BaseModel):
    """
    Output from the Research Agent.
    
    Contains all sources found, key findings extracted, and a summary.
    This will be passed to the Assessment Agent for risk evaluation.
    """
    player_name: str = Field(..., description="Player being researched")
    sources: List[Source] = Field(
        default_factory=list, 
        description="List of source citations found"
    )
    key_findings: List[str] = Field(
        default_factory=list,
        description="Bullet points of important information extracted"
    )
    summary: str = Field(
        ..., 
        description="2-3 sentence overview of the injury status"
    )
    search_timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When this research was conducted"
    )
    confidence_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Confidence in findings (0.0 = no info, 1.0 = very confident)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "player_name": "Jack Currie",
                "sources": [
                    {
                        "url": "https://twitter.com/OxfordUnited/status/123456",
                        "title": "Oxford United Official",
                        "snippet": "Jack Currie participated in full training",
                        "published_date": "2025-11-27T14:30:00",
                        "source_type": "twitter"
                    }
                ],
                "key_findings": [
                    "Participated in full training on Nov 27",
                    "No injury concerns mentioned in press conference",
                    "Expected to be available for Friday's match"
                ],
                "summary": "Jack Currie appears fully fit with no injury concerns. Participated in full training and is expected to be available for the Ipswich Town fixture.",
                "search_timestamp": "2025-11-27T16:00:00",
                "confidence_score": 0.85
            }
        }
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return self.model_dump(mode='json')

