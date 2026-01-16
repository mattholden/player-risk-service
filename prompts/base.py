from abc import ABC, abstractmethod
from dataclasses import dataclass

class AgentPrompt(ABC):
    """Contract: Every agent must have a system + user template."""

    @abstractmethod
    def system_prompt_template(self) -> str: ...

    @abstractmethod
    def user_prompt_template(self) -> str: ...

@dataclass
class SportConfig:
    """Groups all agent prompts for a specific sport."""

    name: str
    research: AgentPrompt
    analyst: AgentPrompt
    shark: AgentPrompt

