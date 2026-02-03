"""
Pydantic data models for agent inputs and outputs.

These models provide type validation, serialization, and clear contracts
between different parts of the agent pipeline.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from database.enums import AlertLevel


class AgentResponseError(Exception):
    """
    Raised when an agent returns an invalid response after exhausting retries.
    
    This exception bubbles up to the fixture-level retry logic in pipeline.py.
    """
    def __init__(self, agent_name: str, reason: str):
        self.agent_name = agent_name
        self.reason = reason
        super().__init__(f"{agent_name} failed: {reason}")


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
    opponent: str = Field(..., description="Opponent team name")
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
    findings: dict = Field(
        default_factory=dict,
        description = "Findings from the research as a dictionary"
    )
    sources: List[str] = Field(
        default_factory=list, 
        description = "List of sources"
    )
    usage: dict = Field(
        default_factory=dict,
        description="Usage data from the grok client"
    )
    grok_client_tool_calls: dict = Field(
        default_factory=dict,
        description="Tool calls from the grok client"
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
                "usage": {"total_tokens": 1000, "completion_tokens": 500, "reasoning_tokens": 300, "prompt_tokens": 200},
                "grok_client_tool_calls": {"server_side_tool_calls": {"tool_name": 10}, "client_side_tool_calls": {"tool_name": 20}},
                "search_timestamp": "2025-11-27T16:00:00"
            }
        }

class TeamAnalysis(BaseModel):
    """
    Output from the analysis agent
    """
    team_name: str = Field(..., description="Team being analyzed")
    opponent_name: str = Field(..., description="Opponent team being analyzed")
    fixture: str = Field(..., description="Fixture being analyzed")
    team_analysis: str = Field(..., description="Analysis of the team's performance")
    usage: dict = Field(
        default_factory=dict,
        description="Usage data from the grok client"
    )
    grok_client_tool_calls: dict = Field(
        default_factory=dict,
        description="Tool calls from the grok client"
    )
    class Config:
        json_schema_extra = {
            "example": {
                "team_name": "Arsenal",
                "opponent_name": "Brentford",
                "fixture": "Arsenal vs Brentford",
                "team_analysis": "Arsenal is a strong team and will win the match",
                "usage": {"total_tokens": 1000, "completion_tokens": 500, "reasoning_tokens": 300, "prompt_tokens": 200, "server_tool_calls": 10, "client_tool_calls": 20},
                "grok_client_tool_calls": {"server_side_tool_calls": {"tool_name": 10}, "client_side_tool_calls": {"tool_name": 10}}
            }
        }
class PlayerAlert(BaseModel):
    """
    Output from the shark agent
    """
    player_name: str = Field(..., description="Player being analyzed")
    fixture: str = Field(..., description="Fixture of the player")
    fixture_date: datetime = Field(..., description="Date and time of the fixture")
    alert_level: AlertLevel = Field(..., description="Risk of the player playing in the fixture")
    description: str = Field(..., description="Description of the risk")


    class Config:
        json_schema_extra = {
            "example": {
                "player_name": "Jack Currie",
                "fixture": "Oxford United vs Ipswich Town",
                "fixture_date": "2025-11-28T19:45:00",
                "alert_level": AlertLevel.HIGH_ALERT,
                "description": "Jack Currie is ruled out for the next 2 weeks"
            }
        }

class SharkAgentResponse(BaseModel):
    """
    Output from the shark agent
    """
    alerts: Optional[List[PlayerAlert]] = Field(default=[], description="List of player alerts")
    usage: Optional[dict] = Field(default={}, description="Usage data from the shark agent")
    grok_client_tool_calls: Optional[dict] = Field(default={}, description="Tool calls from the grok client")
    class Config:
        json_schema_extra = {
            "example": {
                "alerts": [PlayerAlert(player_name="Jack Currie", fixture="Oxford United vs Ipswich Town", fixture_date="2025-11-28T19:45:00", alert_level=AlertLevel.HIGH_ALERT, description="Jack Currie is ruled out for the next 2 weeks")],
                "usage": {"total_tokens": 1000, "completion_tokens": 500, "reasoning_tokens": 300, "prompt_tokens": 200, "server_tool_calls": 10, "client_tool_calls": 20},
                "grok_client_tool_calls": {"server_side_tool_calls": {"tool_name": 10}, "client_side_tool_calls": {"tool_name": 10}}
            }
        }

class TeamData(BaseModel):
    """
    Data for a single team analysis (two per fixture/match).
    """
    team_a: str = Field(..., description="Team A being analyzed")
    team_b: str = Field(..., description="Team B being analyzed")
    injury_news: Optional[str] = Field(default=None, description="Injury news from research agent")
    analyst_report: Optional[str] = Field(default=None, description="Report from analyst agent")
    
#TODO: HOW DO WE MAKE THIS SPORTS AGNOSTIC?
class AgentData(BaseModel):
    """
    Data for the agent pipeline. Fields populated progressively.
    """
    # Required at creation (from fixture data)
    fixture: str = Field(..., description="Fixture string e.g. 'Arsenal vs Brentford'")
    match_time: datetime = Field(..., description="Parsed match datetime")
    
    # Optional - populated later
    team_contexts: Optional[List['TeamContext']] = Field(default=None, description="List of team contexts")
    current_date: datetime = Field(default_factory=datetime.now, description="Current date")
    lookback_days: int = Field(default=14, description="Number of days to look back")
    lookback_date: Optional[datetime] = Field(default=None, description="Calculated lookback date")
    injury_news: Optional[str] = Field(default=None, description="Injury news from research agent")
    analyst_report: Optional[str] = Field(default=None, description="Report from analyst agent")

class AnalystPromptPlaceholders(BaseModel):
    """
    Placeholders for the prompt templates
    """
    fixture: str = Field(..., description="Fixture being analyzed")
    fixture_date: datetime = Field(..., description="Date and time of the fixture")
    team: str = Field(..., description="Team being analyzed")
    opponent: str = Field(..., description="Opponent team being analyzed")
    current_date: datetime = Field(..., description="Current date")
    injury_news: str = Field(..., description="Injury news")

class AgentUsage(BaseModel):
    """
    Usage data (tokens, server calls, etc.) for an agent.
    """
    agent_name: str = Field(..., description="Name of the agent")
    total_tokens: int = Field(..., description="Total tokens used")
    completion_tokens: int = Field(..., description="Completion tokens used")
    reasoning_tokens: int = Field(..., description="Reasoning tokens used")
    prompt_tokens: int = Field(..., description="Prompt tokens used")
    server_side_tool_calls: dict = Field(
        default_factory=dict,
        description="Server side tool calls from the grok client"
    )
    client_side_tool_calls: dict = Field(
        default_factory=dict,
        description="Client side tool calls from the grok client"
    )
    completion_timestamp: datetime = Field(..., description="Timestamp of the usage")

class FixtureUsage(BaseModel):
    """
    Usage data across all agents for a fixture.
    """
    fixture: Optional[str] = Field(default=None, description="Fixture being analyzed")
    match_time: Optional[datetime] = Field(default=None, description="Parsed match datetime")
    agent_usages: Optional[List[AgentUsage]] = Field(default=None, description="Usage data for each agent")
    start_timestamp: Optional[datetime] = Field(default=None, description="Timestamp of the start of the fixture")
    
    class Config:
        json_schema_extra = {
            "example": {
                "fixture": "Arsenal vs Brentford",
                "match_time": "2025-11-28T19:45:00",
                "agent_usages": [
                    {
                        "agent_name": "research_agent_1",
                        "total_tokens": 1000,
                        "completion_tokens": 500,
                        "reasoning_tokens": 300,
                        "prompt_tokens": 200,
                        "server_side_tool_usage": {"tool_name": "tool_name", "usage": 10},
                        "completion_timestamp": "2025-11-28T19:45:00"
                    }
                ]
            }
        }

class PipelineUsage(BaseModel):
    """
    Usage data across all fixtures and agents for a pipeline run.
    """
    run_id: str = Field(..., description="ID of the pipeline run")
    fixture_usages: List[FixtureUsage] = Field(..., description="Usage data for each fixture")
    completion_timestamp: datetime = Field(..., description="Timestamp of the completion of the pipeline")
    
    class Config:
        json_schema_extra = {
            "example": {
                "run_id": "1234567890",
                "fixture_usages": [
                    {
                        "fixture": "Arsenal vs Brentford",
                        "match_time": "2025-11-28T19:45:00",
                        "agent_usages": [
                            {
                                "agent_name": "research_agent_1",
                                "total_tokens": 1000,
                                "completion_tokens": 500,
                                "reasoning_tokens": 300,
                                "prompt_tokens": 200,
                                "server_side_tool_usage": {"tool_name": "tool_name", "usage": 10},
                                "completion_timestamp": "2025-11-28T19:45:00"
                            }
                        ],
                        "completion_timestamp": "2025-11-28T19:45:00"
                    }
                ],
                "completion_timestamp": "2025-11-28T19:45:00"
            }
        }