"""
Clients package - External API integrations.

Handles communication with:
- NewsAPI: Sports news articles
- Grok (xAI): LLM research and risk analysis with X/Twitter search
- OpenAI/Anthropic: Alternative LLM providers (future)
"""

from .grok_client import GrokClient

__all__ = ['GrokClient']

