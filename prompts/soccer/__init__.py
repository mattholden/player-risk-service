from prompts.base import SportConfig
from prompts.soccer.research import SoccerResearchPrompt
from prompts.soccer.analyst import SoccerAnalystPrompt
from prompts.soccer.shark import SoccerSharkPrompt

SOCCER = SportConfig(
    name="soccer",
    research=SoccerResearchPrompt(),
    analyst=SoccerAnalystPrompt(),
    shark=SoccerSharkPrompt(),
)