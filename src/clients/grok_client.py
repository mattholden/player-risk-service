"""
Grok API Client - Low-level wrapper for xAI's Grok API.

This client handles:
- Authentication with xAI API
- Rate limiting (100 requests/hour for development)
- Retry logic with exponential backoff
- Error handling and response validation
- Native tool support (web_search, x_search, code_execution)

Using the native xAI SDK for better integration with Grok's features.
"""

import os
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from xai_sdk import Client  # type: ignore
from xai_sdk.chat import user, system  # type: ignore
from xai_sdk.tools import web_search, x_search  # type: ignore
from tenacity import (  # type: ignore
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""
    pass


class GrokClient:
    """
    Client for interacting with xAI's Grok API using native xAI SDK.
    
    Usage:
        client = GrokClient(api_key="your-key")
        response = client.chat_completion(
            messages=[{"role": "user", "content": "Hello!"}],
            use_web_search=True
        )
    """
    
    # Rate limiting settings
    MAX_REQUESTS_PER_HOUR = 100
    REQUEST_WINDOW_SECONDS = 3600  # 1 hour
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        model: str = "grok-4-1-fast-reasoning",
        max_tokens: int = 2500,
        temperature: float = 0.8
    ):
        """
        Initialize Grok API client.
        
        Args:
            api_key: xAI API key (defaults to XAI_API_KEY or GROK_API_KEY env var)
            model: Model to use (grok-4-1-fast-reasoning, grok-4-1-fast, etc.)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0-1.0, lower = more factual)
        """
        # Try both XAI_API_KEY and GROK_API_KEY for backwards compatibility
        self.api_key = os.getenv('GROK_API_KEY', '').strip()
        
        if not self.api_key:
            raise ValueError(
                "API key must be provided or set as XAI_API_KEY or GROK_API_KEY environment variable"
            )
        
        # Initialize xAI client
        self.client = Client(api_key=self.api_key)
        
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        # Rate limiting tracking
        self._request_timestamps: List[datetime] = []
        
        print(f"✅ GrokClient initialized (model: {model}, using xAI SDK)")
    
    def _check_rate_limit(self) -> None:
        """
        Check if we're within rate limits.
        
        Raises:
            RateLimitExceeded: If rate limit would be exceeded
        """
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.REQUEST_WINDOW_SECONDS)
        
        # Remove timestamps outside the window
        self._request_timestamps = [
            ts for ts in self._request_timestamps if ts > cutoff
        ]
        
        if len(self._request_timestamps) >= self.MAX_REQUESTS_PER_HOUR:
            oldest = self._request_timestamps[0]
            wait_seconds = (oldest + timedelta(seconds=self.REQUEST_WINDOW_SECONDS) - now).total_seconds()
            raise RateLimitExceeded(
                f"Rate limit exceeded. {len(self._request_timestamps)}/{self.MAX_REQUESTS_PER_HOUR} "
                f"requests in last hour. Wait {wait_seconds:.0f} seconds."
            )
        
        # Record this request
        self._request_timestamps.append(now)
    
    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        use_web_search: bool = True,
        use_x_search: bool = True,
        return_citations: bool = True,
        max_search_results: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a chat completion request to Grok with native tool support.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Override default model
            max_tokens: Override default max_tokens
            temperature: Override default temperature
            use_web_search: Enable web search tool (default: True)
            use_x_search: Enable X/Twitter search tool (default: True)
            return_citations: Include citations in response (default: True)
            max_search_results: Max number of search results (default: 10)
            **kwargs: Additional parameters to pass to API
        
        Returns:
            API response dictionary with content, sources, usage, etc.
            
        Raises:
            RateLimitExceeded: If rate limit exceeded
            Exception: If API call fails after retries
        """
        # Check rate limit
        self._check_rate_limit()
        
        # Use defaults if not overridden
        model = model or self.model
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature
        
        # Build tools list - tools don't take parameters, they're just instances
        tools = []
        if use_web_search:
            tools.append(web_search())
        if use_x_search:
            tools.append(x_search())
        
        try:
            # Create chat with tools
            chat = self.client.chat.create(
                model=model,
                tools=tools if tools else None,
            )
            
            # Add messages to the chat using the correct API
            for message in messages:
                role = message.get('role', 'user')
                content = message.get('content', '')
                
                if role == 'system':
                    chat.append(system(content))
                elif role == 'user':
                    chat.append(user(content))
    
            
            # Get the response by sampling
            response = chat.sample()
            
            return self._parse_response(response)
            
        except Exception as e:
            print(f"❌ Grok API error: {e}")
            raise
    
    def _parse_response(self, response) -> Dict[str, Any]:
        """
        Parse xAI SDK response into a clean dictionary.
        
        Args:
            response: xAI SDK response object (from chat.sample())
            chat: xAI SDK chat object
            
        Returns:
            Dictionary with parsed response data
        """
        # Extract content from response
        # The response object has a .content attribute

    
        try:
            content = response.content
        except Exception as e:
            print(f"⚠️  Could not extract content: {e}")
            content = ""
        try:
            sources = response.citations
        except Exception as e:
            print(f"⚠️  Could not extract sources: {e}")
            sources = []
        # Try to extract usage stats if available
        try:
            usage = response.usage

        except Exception as e:
            print(f"⚠️  Could not extract usage stats: {e}")
            usage = {}
        
        return {
            "content": content,
            "role": "assistant",
            "model": self.model,
            "sources": sources,
            "usage": usage,
            "created_at": datetime.now()
        }
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """
        Get current rate limit status.
        
        Returns:
            Dictionary with rate limit info
        """
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.REQUEST_WINDOW_SECONDS)
        
        # Clean old timestamps
        self._request_timestamps = [
            ts for ts in self._request_timestamps if ts > cutoff
        ]
        
        remaining = self.MAX_REQUESTS_PER_HOUR - len(self._request_timestamps)
        
        return {
            "requests_made": len(self._request_timestamps),
            "requests_remaining": remaining,
            "limit": self.MAX_REQUESTS_PER_HOUR,
            "window_seconds": self.REQUEST_WINDOW_SECONDS,
            "reset_time": (
                self._request_timestamps[0] + timedelta(seconds=self.REQUEST_WINDOW_SECONDS)
                if self._request_timestamps else now
            )
        }


def test_client():
    """Quick test function to verify API connectivity."""
    try:
        client = GrokClient()
        
        print("\n📊 Rate Limit Status:")
        status = client.get_rate_limit_status()
        print(f"  Remaining: {status['requests_remaining']}/{status['limit']}")
        
        print("\n🔍 Testing simple query...")
        response = client.chat_completion(
            messages=[
                {"role": "user", "content": "Say 'Hello from Grok!' in one sentence."}
            ],
            use_web_search=False,
            use_x_search=False
        )
        
        print(f"\n✅ Response: {response['content']}")
        print(f"📈 Tokens used: {response['usage']['total_tokens']}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Run test if this file is executed directly
    test_client()
