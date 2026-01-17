from abc import ABC, abstractmethod
from dataclasses import dataclass
from src.utils.strict_prompting import strict_format

class AgentPrompt(ABC):
    """Contract: Every agent must have a system + user template."""

    @abstractmethod
    def system_prompt_template(self) -> str: ...

    @abstractmethod
    def user_prompt_template(self) -> str: ...

    @abstractmethod
    def get_system_values(self, **kwargs) -> dict:
        """
        Returns dictionary of placeholder values for system template.
        If no placeholders used in system prompt, return empty dict.
        """
        ...

    @abstractmethod
    def get_user_values(self, **kwargs) -> dict:
        """
        Returns dictionary of placeholder values for user template.
        If no placeholders used in user prompt, return empty dict.
        """
        ...

    #Inherited and always called from Agent pipeline
    def generate_system_prompt(self, **kwargs) -> dict:
        """Formats system prompt. Always uses strict_format from src.utils.strict_prompting."""
        content = strict_format(
            self.system_prompt_template(),
            **self.get_system_values(**kwargs)
        )
        return {"role": "system", "content": content}

    #Inherited and always called from Agent pipeline
    def generate_user_prompt(self, **kwargs) -> dict:
        """Formats user prompt. Always uses strict_format from src.utils.strict_prompting."""
        content = strict_format(
            self.user_prompt_template(),
            **self.get_user_values(**kwargs)
        )
        return {"role": "user", "content": content}

@dataclass
class SportConfig:
    """Groups all agent prompts for a specific sport."""

    name: str
    research: AgentPrompt
    analyst: AgentPrompt
    shark: AgentPrompt

