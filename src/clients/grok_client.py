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
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import json
from xai_sdk import Client, AsyncClient  # type: ignore
from xai_sdk.chat import user, system, tool_result  # type: ignore
from xai_sdk.tools import web_search, x_search  # type: ignore
from xai_sdk.tools import get_tool_call_type  # type: ignore
from tenacity import (  # type: ignore
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
from xai_sdk.proto import chat_pb2
from src.logging import get_logger


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
    REQUEST_WINDOW_SECONDS = 3600
    NATIVE_TOOLS = {
                    'web_search', 'x_search', 'x_semantic_search', 
                    'x_keyword_search', 'analyze_x_posts'
                }  # 1 hour
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        model: str = "grok-4-1-fast-reasoning",
        max_tokens: int = 2500,
        temperature: float = 0.8,
        max_turns: int = 5,
        parallel_tool_calls: bool = True,
        reasoning_effort: str = "high",
        max_iterations: int = 10,
        async_timeout: float = 180.0
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
        self.logger = get_logger()
        
        if not self.api_key:
            raise ValueError(
                "API key must be provided or set as XAI_API_KEY or GROK_API_KEY environment variable"
            )
        
        # Initialize xAI client
        self.client = Client(api_key=self.api_key)
        self._async_client: Optional[AsyncClient] = None
        self._async_client_loop: Optional[asyncio.AbstractEventLoop] = None
        
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        # Rate limiting tracking
        self._request_timestamps: List[datetime] = []
        
        self.logger.success(f"Grok Client Initialized (model: {model}, using xAI SDK)")

        self.server_side_tool_calls: dict[str, int] = {}

        # Agent Settings
        self.max_turns = max_turns
        self.parallel_tool_calls = parallel_tool_calls
        self.reasoning_effort = reasoning_effort
        self.max_iterations = max_iterations
        self.async_timeout = async_timeout


    def _get_async_client(self) -> AsyncClient:
        """
        Get AsyncClient, creating fresh one if needed.
        Handles event loop changes (e.g., multiple asyncio.run() calls).
        """
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            raise RuntimeError("_get_async_client must be called from async context")
        
        # Create new client if none exists or loop changed
        if self._async_client is None or self._async_client_loop != current_loop:
            self._async_client = AsyncClient(api_key=self.api_key)
            self._async_client_loop = current_loop
            self.logger.debug("Created new AsyncClient for current event loop")
        
        return self._async_client

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

    def chat_with_streaming(
            self,
            messages: List[Dict[str, str]],
            tool_registry: Optional[Any] = None,
            model: Optional[str] = None,
            use_web_search: bool = True,
            use_x_search: bool = True,
            verbose: bool = False,
            **kwargs
        ) -> Dict[str, Any]:
        """
        Chat with streaming response from Grok.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            tool_registry: ToolRegistry instance with registered tools
            model: Override default model
            use_web_search: Enable web search tool (default: True)
            use_x_search: Enable X/Twitter search tool (default: True)
            max_iterations: Max agent loop iterations (default: 10)
            verbose: Print debug output (default: False)
            **kwargs: Additional parameters
        """
        # Check rate limit
        self._check_rate_limit()
        # Build tools list
        tools = []
        if use_web_search:
            tools.append(web_search())
        if use_x_search:
            tools.append(x_search())
        
        # Add custom tools from registry
        if tool_registry:
            custom_tools = tool_registry.get_all_client_side_tools()
            custom_tools_names = tool_registry.get_tool_names()
            tools.extend(custom_tools)

        chat = self.client.chat.create(
            model=self.model,
            tools=tools if tools else None,
            reasoning_effort=self.reasoning_effort,
            max_turns=self.max_turns,
            parallel_tool_calls=self.parallel_tool_calls
        )

        for message in messages:
            role = message.get('role', 'user')
            content = message.get('content', '')
            if role == 'system':
                chat.append(system(content))
            elif role == 'user':
                chat.append(user(content))

        research_turns = 0
        server_side_tool_call_tracking = {}
        client_side_tool_call_tracking = {}
        
        while True:
            research_turns += 1
            server_side_tool_call_tracking[f"Turn {research_turns}"] = {}
            client_side_tool_call_tracking[f"Turn {research_turns}"] = {}
            client_side_tool_calls = []
            
            for response, chunk in chat.stream():
                for tool_call in chunk.tool_calls:
                    tool_type = get_tool_call_type(tool_call)
                    if tool_type == "client_side_tool":
                        client_side_tool_calls.append(tool_call)
                        client_side_tool_call_tracking[f"Turn {research_turns}"][tool_call.function.name] = client_side_tool_call_tracking[f"Turn {research_turns}"].get(tool_call.function.name, 0) + 1
                       
                    else:
                        server_side_tool_call_tracking[f"Turn {research_turns}"][tool_call.function.name] = server_side_tool_call_tracking[f"Turn {research_turns}"].get(tool_call.function.name, 0) + 1
                    
            self.logger.grok_client_tool_calls(research_turns, client_side_tool_call_tracking, server_side_tool_call_tracking)
            
            chat.append(response)
            
            # If no client-side tools were called, we're done
            if not client_side_tool_calls:
                self.logger.success("Grok Streaming Complete")
                break
            
            # Execute your custom tools and add results
            self.logger.debug(f"Executing {len(client_side_tool_calls)} client-side tool(s):")
            for tool_call in client_side_tool_calls:
                self.logger.debug(f"      → {tool_call.function.name}")
                if tool_call.function.name in custom_tools_names:
                    result = tool_registry.execute(tool_call.function.name, json.loads(tool_call.function.arguments))
                    chat.append(tool_result(result))
                else:
                    self.logger.warning(f"Unknown tool: {tool_call.function.name}")
                    continue
            
        # Convert SDK usage objects to dicts
        raw_usage = getattr(response, 'usage', None)
        usage_dict = {}
        if raw_usage:
            usage_dict = {
                'total_tokens': getattr(raw_usage, 'total_tokens', 0),
                'completion_tokens': getattr(raw_usage, 'completion_tokens', 0),
                'reasoning_tokens': getattr(raw_usage, 'reasoning_tokens', 0),
                'prompt_tokens': getattr(raw_usage, 'prompt_tokens', 0),
            }
        
        # Tools Calls
        grok_client_tool_calls = {
                "server_side_tool_calls": server_side_tool_call_tracking,
                "client_side_tool_calls": client_side_tool_call_tracking,
        }


        return {
            "content": response.content,
            "role": "assistant",
            "model": self.model,
            "sources": getattr(response, 'citations', []),
            "usage": usage_dict,
            "grok_client_tool_calls": grok_client_tool_calls,
            "created_at": datetime.now()
        }

    async def chat_with_agent(
        self,
        messages: List[Dict[str, str]],
        tool_registry: Optional[Any] = None,
        model: Optional[str] = None,
        use_web_search: bool = True,
        use_x_search: bool = True,
        max_iterations: int = 10,
        verbose: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Async function for concurrent chats with grok client
        """
        self._check_rate_limit()

        async def _execute():

            async_client = self._get_async_client()

            tools = []
            if use_web_search:
                tools.append(web_search())
            if use_x_search:
                tools.append(x_search())

            if tool_registry:
                custom_tools = tool_registry.get_all_client_side_tools()
                custom_tools_names = tool_registry.get_tool_names()
                tools.extend(custom_tools)

            chat = async_client.chat.create(
                model=self.model,
                tools=tools if tools else None,
                reasoning_effort=self.reasoning_effort,
                max_turns=self.max_turns,
                parallel_tool_calls=self.parallel_tool_calls
            )

            for message in messages:
                role = message.get('role', 'user')
                content = message.get('content', '')
                if role == 'system':
                    chat.append(system(content))
                elif role == 'user':
                    chat.append(user(content))

            research_turns = 0
            server_side_tool_call_tracking = {}
            client_side_tool_call_tracking = {}

            while True:
                research_turns += 1
                server_side_tool_call_tracking[f"Turn {research_turns}"] = {}
                client_side_tool_call_tracking[f"Turn {research_turns}"] = {}
                client_side_tool_calls = []

                response = await chat.sample()

                if response.tool_calls:
                    for tool_call in response.tool_calls:
                        tool_type = get_tool_call_type(tool_call)
                        if tool_type == "client_side_tool":
                            client_side_tool_calls.append(tool_call)
                            client_side_tool_call_tracking[f"Turn {research_turns}"][tool_call.function.name] = client_side_tool_call_tracking[f"Turn {research_turns}"].get(tool_call.function.name, 0) + 1
                        elif tool_type == "server_side_tool":
                            server_side_tool_call_tracking[f"Turn {research_turns}"][tool_call.function.name] = server_side_tool_call_tracking[f"Turn {research_turns}"].get(tool_call.function.name, 0) + 1
                        else:
                            self.logger.warning(f"Unknown tool type: {tool_type}")
                            continue

                self.logger.grok_client_tool_calls(research_turns, client_side_tool_call_tracking, server_side_tool_call_tracking)

                chat.append(response)

                if not client_side_tool_calls:
                    self.logger.success("Grok Agent Complete")
                    break

                self.logger.debug(f"Executing {len(client_side_tool_calls)} client-side tool(s):")
                for tool_call in client_side_tool_calls:
                    self.logger.debug(f"      → {tool_call.function.name}")
                    if tool_call.function.name in custom_tools_names:
                        result = tool_registry.execute(tool_call.function.name, json.loads(tool_call.function.arguments))
                        chat.append(tool_result(result))
                    else:
                        self.logger.warning(f"Unknown tool: {tool_call.function.name}")
                        continue
            
            # Convert SDK usage objects to dicts
            raw_usage = getattr(response, 'usage', None)
            usage_dict = {}
            if raw_usage:
                usage_dict = {
                    'total_tokens': getattr(raw_usage, 'total_tokens', 0),
                    'completion_tokens': getattr(raw_usage, 'completion_tokens', 0),
                    'reasoning_tokens': getattr(raw_usage, 'reasoning_tokens', 0),
                    'prompt_tokens': getattr(raw_usage, 'prompt_tokens', 0),
                }
            
            # Tools Calls
            grok_client_tool_calls = {
                    "server_side_tool_calls": server_side_tool_call_tracking,
                    "client_side_tool_calls": client_side_tool_call_tracking,
            }


            return {
                "content": response.content,
                "role": "assistant",
                "model": self.model,
                "sources": getattr(response, 'citations', []),
                "usage": usage_dict,
                "grok_client_tool_calls": grok_client_tool_calls,
                "created_at": datetime.now()
            }

        try:
            return await asyncio.wait_for(_execute(), timeout=self.async_timeout)
        except asyncio.TimeoutError:
            self.logger.error(f"Grok agent timed out after {self.async_timeout}s")
            # Return a response structure that callers can handle
            return {
                "content": "",
                "role": "assistant",
                "model": self.model,
                "sources": [],
                "usage": {},
                "grok_client_tool_calls": {},
                "created_at": datetime.now(),
                "error": "timeout",  # Flag for callers to check
                "error_message": f"Request timed out after {self.async_timeout} seconds"
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


