from prompts.base import SportConfig, AgentPrompt
from prompts.soccer import SOCCER

# Registry of all sports
_SPORTS = {
    "soccer": SOCCER,
    # "football": FOOTBALL,
    # "basketball": BASKETBALL,
    # "tennis": TENNIS,
    # etc
}

def get_sport_config(sport: str) -> SportConfig:
    """Get the prompting templates for a sport"""
    if sport not in _SPORTS:
        raise ValueError(f"Unknown sport: {sport},  Available: {list(_SPORTS.keys())}")
    return _SPORTS[sport]