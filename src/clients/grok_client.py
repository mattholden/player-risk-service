"""
Grok API Client - Low-level wrapper for xAI's Grok API.

This client handles:
- Authentication with xAI API
- Rate limiting (100 requests/hour for development)
- Retry logic with exponential backoff
- Error handling and response validation

The xAI API is compatible with OpenAI's SDK, so we use the openai library.
"""

import os
import time
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from openai import OpenAI
import httpx
from tenacity import (
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
    Client for interacting with xAI's Grok API.
    
    Usage:
        client = GrokClient(api_key="your-key")
        response = client.chat_completion(
            messages=[{"role": "user", "content": "Hello!"}]
        )
    """
    
    # Rate limiting settings
    MAX_REQUESTS_PER_HOUR = 100
    REQUEST_WINDOW_SECONDS = 3600  # 1 hour
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        model: str = "grok-4-1-fast-reasoning",
        max_tokens: int = 2000,
        temperature: float = 0.8
    ):
        """
        Initialize Grok API client.
        
        Args:
            api_key: xAI API key (defaults to GROK_API_KEY env var)
            model: Model to use (grok-beta, grok-2, etc.)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0-1.0, lower = more factual)
        """
        self.api_key = (api_key or os.getenv('GROK_API_KEY', '')).strip()
        if not self.api_key:
            raise ValueError(
                "GROK_API_KEY must be provided or set in environment variables"
            )
        
        # Create httpx client explicitly to avoid proxy issues
        http_client = httpx.Client(
            base_url="https://api.x.ai/v1",
            timeout=60.0,
            follow_redirects=True
        )
        
        # Initialize OpenAI client with explicit httpx client
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.x.ai/v1",
            http_client=http_client
        )
        
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        # Rate limiting tracking
        self._request_timestamps: List[datetime] = []
        
        print(f"✅ GrokClient initialized (model: {model})")
    
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
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a chat completion request to Grok.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Override default model
            max_tokens: Override default max_tokens
            temperature: Override default temperature
            **kwargs: Additional parameters to pass to API
        
        Returns:
            API response dictionary
            
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
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                **kwargs
            )
            
            return self._parse_response(response)
            
        except Exception as e:
            print(f"❌ Grok API error: {e}")
            raise
    
    def _parse_response(self, response) -> Dict[str, Any]:
        """
        Parse OpenAI SDK response into a clean dictionary.
        
        Args:
            response: OpenAI ChatCompletion response object
            
        Returns:
            Dictionary with parsed response data
        """
        choice = response.choices[0]

        return {
            "content": choice.message.content,
            "role": choice.message.role,
            "model": response.model,
            "finish_reason": choice.finish_reason,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            "created_at": datetime.fromtimestamp(response.created)
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
            ]
        )
        
        print(f"\n✅ Response: {response['content']}")
        print(f"📈 Tokens used: {response['usage']['total_tokens']}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


if __name__ == "__main__":
    # Run test if this file is executed directly
    test_client()

