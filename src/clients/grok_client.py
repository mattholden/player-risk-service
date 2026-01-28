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
import json
from xai_sdk import Client  # type: ignore
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
        self.logger = get_logger()
        
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
        
        self.logger.success(f"Grok Client Initialized (model: {model}, using xAI SDK)")
    
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
    # def chat_completion(
    #     self,
    #     messages: List[Dict[str, str]],
    #     model: Optional[str] = None,
    #     max_tokens: Optional[int] = None,
    #     temperature: Optional[float] = None,
    #     use_web_search: bool = True,
    #     use_x_search: bool = True,
    #     return_citations: bool = True,
    #     max_search_results: int = 10,
    #     **kwargs
    # ) -> Dict[str, Any]:
    #     """
    #     Send a chat completion request to Grok with native tool support.
        
    #     Args:
    #         messages: List of message dicts with 'role' and 'content'
    #         model: Override default model
    #         max_tokens: Override default max_tokens
    #         temperature: Override default temperature
    #         use_web_search: Enable web search tool (default: True)
    #         use_x_search: Enable X/Twitter search tool (default: True)
    #         return_citations: Include citations in response (default: True)
    #         max_search_results: Max number of search results (default: 10)
    #         **kwargs: Additional parameters to pass to API
        
    #     Returns:
    #         API response dictionary with content, sources, usage, etc.
            
    #     Raises:
    #         RateLimitExceeded: If rate limit exceeded
    #         Exception: If API call fails after retries
    #     """
    #     # Check rate limit
    #     self._check_rate_limit()
        
    #     # Use defaults if not overridden
    #     model = model or self.model
    #     max_tokens = max_tokens or self.max_tokens
    #     temperature = temperature or self.temperature
        
    #     # Build tools list - tools don't take parameters, they're just instances
    #     tools = []
    #     if use_web_search:
    #         tools.append(web_search())
    #     if use_x_search:
    #         tools.append(x_search())
        
    #     try:
    #         # Create chat with tools
    #         chat = self.client.chat.create(
    #             model=model,
    #             tools=tools if tools else None,
    #         )
            
    #         # Add messages to the chat using the correct API
    #         for message in messages:
    #             role = message.get('role', 'user')
    #             content = message.get('content', '')
                
    #             if role == 'system':
    #                 chat.append(system(content))
    #             elif role == 'user':
    #                 chat.append(user(content))
    
            
    #         # Get the response by sampling
    #         response = chat.sample()
            
    #         return self._parse_response(response)
            
    #     except Exception as e:
    #         self.logger.error(f"Grok API error: {e}")
    #         raise
    
    # def chat_with_tools(
    #     self,
    #     messages: List[Dict[str, str]],
    #     tool_registry: Optional[Any] = None,
    #     model: Optional[str] = None,
    #     use_web_search: bool = True,
    #     use_x_search: bool = True,
    #     max_iterations: int = 10,
    #     verbose: bool = False,
    #     **kwargs
    # ) -> Dict[str, Any]:
    #     """
    #     Chat with custom tools enabled. Runs an agent loop that continues
    #     until the LLM is done reasoning (no more tool calls).
        
    #     This method:
    #     1. Creates a chat with native tools + custom tools from registry
    #     2. Runs the agent loop (multiple sample() calls as needed)
    #     3. Executes custom tool calls via the registry
    #     4. Returns the final response when LLM is done
        
    #     Args:
    #         messages: List of message dicts with 'role' and 'content'
    #         tool_registry: ToolRegistry instance with registered tools
    #         model: Override default model
    #         use_web_search: Enable web search tool (default: True)
    #         use_x_search: Enable X/Twitter search tool (default: True)
    #         max_iterations: Max agent loop iterations (default: 10)
    #         verbose: Print debug output (default: False)
    #         **kwargs: Additional parameters
            
    #     Returns:
    #         API response dictionary with content, sources, usage, etc.
            
    #     Raises:
    #         RateLimitExceeded: If rate limit exceeded
    #         Exception: If API call fails or max iterations reached
    #     """
    #     # Check rate limit
    #     self._check_rate_limit()
        
    #     # Use defaults if not overridden
    #     model = model or self.model
        
    #     # Build tools list
    #     tools = []
        
    #     # Add custom tools from registry
    #     if tool_registry:
    #         custom_tools = tool_registry.get_all_protobufs()
    #         tools.extend(custom_tools)
    #         if verbose:
    #             print(f"   🔧 Loaded {len(custom_tools)} custom tools: {tool_registry.get_tool_names()}")
        
    #     # IMPORTANT: Don't mix native and custom tools - they conflict
    #     # Native tools should be used via chat_completion() separately
    #     if (use_web_search or use_x_search) and tool_registry:
    #         if verbose:
    #             print("   ⚠️  Native tools (web/X search) disabled when custom tools are present")
    #             print("      Use chat_completion() separately for web/X searches")
    #     elif use_web_search or use_x_search:
    #         # Only add native tools if NO custom tools
    #         if use_web_search:
    #             tools.append(web_search())
    #         if use_x_search:
    #             tools.append(x_search())
        
    #     try:
    #         # Create chat with all tools
    #         chat = self.client.chat.create(
    #             model=model,
    #             tools=tools if tools else None,

    #         )
            
    #         # Add messages to the chat
    #         for message in messages:
    #             role = message.get('role', 'user')
    #             content = message.get('content', '')
                
    #             if role == 'system':
    #                 chat.append(system(content))
    #             elif role == 'user':
    #                 chat.append(user(content))
            
    #         # Run the agent loop
    #         for iteration in range(1, max_iterations + 1):
    #             if verbose:
    #                 print(f"\n   🔄 Agent Loop - Iteration {iteration}")
                
    #             # Check rate limit for each iteration
    #             self._check_rate_limit()
                
    #             # Get response from LLM
    #             response = chat.sample()
                
    #             # Check if LLM is done (no tool calls)
    #             if not response.tool_calls:
    #                 if verbose:
    #                     print("   ✅ LLM finished reasoning")
    #                 return self._parse_response(response)
                
    #             # Native tools that are handled server-side by xAI
                
    #             # Separate custom tool calls from native tool calls
    #             custom_tool_calls = [
    #                 tc for tc in response.tool_calls 
    #                 if tc.function.name not in self.NATIVE_TOOLS
    #             ]
    #             native_tool_calls = [
    #                 tc for tc in response.tool_calls 
    #                 if tc.function.name in self.NATIVE_TOOLS
    #             ]
                
    #             if verbose:
    #                 print(f"   🔧 Processing {len(response.tool_calls)} tool call(s)")
    #                 if native_tool_calls:
    #                     print(f"      ℹ️  {len(native_tool_calls)} native tool(s) - handled server-side")
                
    #             # Only process custom tools client-side
    #             for tc in custom_tool_calls:
    #                 tool_name = tc.function.name
    #                 try:
    #                     arguments = json.loads(tc.function.arguments)
    #                 except json.JSONDecodeError:
    #                     arguments = {}
                    
    #                 if verbose:
    #                     print(f"      → {tool_name}({arguments})")
                    
    #                 # Execute the tool via registry
    #                 if tool_registry:
    #                     result = tool_registry.execute(tool_name, arguments)
    #                 else:
    #                     result = json.dumps({"error": f"No registry for tool: {tool_name}"})
                    
    #                 if verbose:
    #                     result_preview = result[:100] + "..." if len(result) > 100 else result
    #                     print(f"      ← {result_preview}")
                    
    #                 # Append result to chat
    #                 chat.append(tool_result(result))
            
    #         # Max iterations reached
    #         raise Exception(f"Agent loop exceeded max iterations ({max_iterations})")
            
    #     except Exception as e:
    #         print(f"❌ Grok API error: {e}")
    #         raise

    def chat_with_streaming(
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
        
        # Use defaults if not overridden
        model = model or self.model
        
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
            model=model,
            tools=tools if tools else None,
            reasoning_effort="high",
            max_turns=5,
            parallel_tool_calls=False
        )

        for message in messages:
            role = message.get('role', 'user')
            content = message.get('content', '')
            if role == 'system':
                chat.append(system(content))
            elif role == 'user':
                chat.append(user(content))

        research_turns = 0
        completion_tokens_list = []
        reasoning_tokens_list = []
        prompt_tokens_list = []
        total_tokens_list = []
        
        while True:
            total_server_side_tool_calls = 0
            total_client_side_tool_calls = 0
            research_turns += 1
            client_side_tool_calls = []
            # previous_usage = None 
            
            for response, chunk in chat.stream():
                current_usage = response.usage
                for tool_call in chunk.tool_calls:
                    tool_type = get_tool_call_type(tool_call)
                    if tool_type == "client_side_tool":
                        client_side_tool_calls.append(tool_call)
                        total_client_side_tool_calls += 1
                    else:
                        total_server_side_tool_calls += 1

                    print(f"Tool Call: {tool_call.function.name} - {tool_type}")
                    print(f"Usage: {current_usage}")
                    print(current_usage.completion_tokens)
                    print(current_usage.reasoning_tokens)
                    print(current_usage.prompt_tokens)
                    print(f"{current_usage.total_tokens}/n")
                    completion_tokens_list.append(current_usage.completion_tokens)
                    reasoning_tokens_list.append(current_usage.reasoning_tokens)
                    prompt_tokens_list.append(current_usage.prompt_tokens)
                    total_tokens_list.append(current_usage.total_tokens)
                    
            self.logger.grok_client_tool_calls(research_turns, total_client_side_tool_calls, total_server_side_tool_calls)
            
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
            
        print(f"Total Tokens List {total_tokens_list}")            
        return {
            "content": response.content,
            "role": "assistant",
            "model": self.model,
            "sources": response.citations,
            "usage": response.usage,
            "server_side_tool_usage": response.server_side_tool_usage,
            "created_at": datetime.now()
        }

    # def _parse_response(self, response) -> Dict[str, Any]:
    #     """
    #     Parse xAI SDK response into a clean dictionary.
        
    #     Args:
    #         response: xAI SDK response object (from chat.sample())
    #         chat: xAI SDK chat object
            
    #     Returns:
    #         Dictionary with parsed response data
    #     """
    #     # Extract content from response
    #     # The response object has a .content attribute

    
    #     try:
    #         content = response.content
    #     except Exception as e:
    #         print(f"⚠️  Could not extract content: {e}")
    #         content = ""
    #     try:
    #         sources = response.citations
    #     except Exception as e:
    #         print(f"⚠️  Could not extract sources: {e}")
    #         sources = []
    #     # Try to extract usage stats if available
    #     try:
    #         usage = response.usage

    #     except Exception as e:
    #         print(f"⚠️  Could not extract usage stats: {e}")
    #         usage = {}

    #     try:
    #         server_side_tool_usage = response.server_side_tool_usage
    #     except Exception as e:
    #         print(f"⚠️  Could not extract server side usage stats: {e}")
    #         server_side_tool_usage = {}
        
    #     return {
    #         "content": content,
    #         "role": "assistant",
    #         "model": self.model,
    #         "sources": sources,
    #         "usage": usage,
    #         "server_side_tool_usage": server_side_tool_usage,
    #         "created_at": datetime.now()
    #     }
    
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


# def test_client():
#     """Quick test function to verify API connectivity."""
#     try:
#         client = GrokClient()
        
#         print("\n📊 Rate Limit Status:")
#         status = client.get_rate_limit_status()
#         print(f"  Remaining: {status['requests_remaining']}/{status['limit']}")
        
#         print("\n🔍 Testing simple query...")
#         response = client.chat_completion(
#             messages=[
#                 {"role": "user", "content": "Say 'Hello from Grok!' in one sentence."}
#             ],
#             use_web_search=False,
#             use_x_search=False
#         )
        
#         print(f"\n✅ Response: {response['content']}")
#         print(f"📈 Tokens used: {response['usage']['total_tokens']}")
        
#         return True
        
#     except Exception as e:
#         print(f"\n❌ Error: {e}")
#         import traceback
#         traceback.print_exc()
#         return False

