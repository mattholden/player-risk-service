"""
Test Custom Tool with xAI SDK - Agent Loop Pattern

This script tests:
1. Defining multiple custom tools
2. Running an agent loop that continues until LLM is done
3. Handling multiple tool calls in sequence
4. Properly matching tool call IDs with responses

Run from project root:
    python -m scripts.test_custom_tool
"""

import os
import json
from typing import Dict, Any, Callable, List
from dotenv import load_dotenv

load_dotenv()


# =============================================================================
# TOOL DEFINITIONS
# =============================================================================

def create_custom_tools():
    """
    Create custom tools using xAI SDK protobuf format.
    
    Returns:
        List of Tool protobuf objects
    """
    from xai_sdk.tools import chat_pb2
    
    tools = []
    
    # Tool 1: Get Active Roster
    tool1 = chat_pb2.Tool()
    tool1.function.name = "get_active_roster"
    tool1.function.description = "Get the current active roster for a sports team. Returns a list of players with their positions."
    tool1.function.parameters = json.dumps({
        "type": "object",
        "properties": {
            "team": {
                "type": "string",
                "description": "The team name, e.g., 'Arsenal'"
            },
            "league": {
                "type": "string",
                "description": "The league name, e.g., 'Premier League'"
            }
        },
        "required": ["team"]
    })
    tools.append(tool1)
    
    # Tool 2: Get Player Injury Status
    tool2 = chat_pb2.Tool()
    tool2.function.name = "get_player_injury_status"
    tool2.function.description = "Check if a specific player is currently injured and their expected return date."
    tool2.function.parameters = json.dumps({
        "type": "object",
        "properties": {
            "player_name": {
                "type": "string",
                "description": "The player's full name"
            },
            "team": {
                "type": "string",
                "description": "The team the player plays for"
            }
        },
        "required": ["player_name"]
    })
    tools.append(tool2)
    
    # Tool 3: Get Upcoming Fixtures
    tool3 = chat_pb2.Tool()
    tool3.function.name = "get_upcoming_fixtures"
    tool3.function.description = "Get the upcoming fixtures/matches for a team."
    tool3.function.parameters = json.dumps({
        "type": "object",
        "properties": {
            "team": {
                "type": "string",
                "description": "The team name"
            },
            "num_fixtures": {
                "type": "integer",
                "description": "Number of upcoming fixtures to return (default: 3)"
            }
        },
        "required": ["team"]
    })
    tools.append(tool3)
    
    return tools


# =============================================================================
# TOOL IMPLEMENTATIONS
# =============================================================================

def get_active_roster(team: str, league: str = None) -> str:
    """Get the active roster for a team."""
    print(f"   📋 Fetching roster for {team}...")
    
    # Mock data
    rosters = {
        "Arsenal": [
            {"name": "David Raya", "position": "Goalkeeper"},
            {"name": "William Saliba", "position": "Centre-Back"},
            {"name": "Gabriel Magalhaes", "position": "Centre-Back"},
            {"name": "Declan Rice", "position": "Defensive Midfield"},
            {"name": "Martin Odegaard", "position": "Attacking Midfield"},
            {"name": "Bukayo Saka", "position": "Right Winger"},
            {"name": "Gabriel Martinelli", "position": "Left Winger"},
            {"name": "Kai Havertz", "position": "Centre-Forward"},
        ],
        "Manchester United": [
            {"name": "Andre Onana", "position": "Goalkeeper"},
            {"name": "Lisandro Martinez", "position": "Centre-Back"},
            {"name": "Bruno Fernandes", "position": "Attacking Midfield"},
            {"name": "Marcus Rashford", "position": "Left Winger"},
        ]
    }
    
    players = rosters.get(team, [{"name": "Unknown", "position": "Unknown"}])
    return json.dumps({"team": team, "league": league or "Unknown", "players": players})


def get_player_injury_status(player_name: str, team: str = None) -> str:
    """Check injury status for a player."""
    print(f"   🏥 Checking injury status for {player_name}...")
    
    # Mock data
    injuries = {
        "Bukayo Saka": {"injured": True, "injury": "Hamstring", "expected_return": "2 weeks"},
        "Martin Odegaard": {"injured": False, "injury": None, "expected_return": None},
        "Gabriel Jesus": {"injured": True, "injury": "Knee", "expected_return": "3 months"},
    }
    
    status = injuries.get(player_name, {"injured": False, "injury": None, "expected_return": None})
    status["player_name"] = player_name
    return json.dumps(status)


def get_upcoming_fixtures(team: str, num_fixtures: int = 3) -> str:
    """Get upcoming fixtures for a team."""
    print(f"   📅 Fetching {num_fixtures} upcoming fixtures for {team}...")
    
    # Mock data
    fixtures = {
        "Arsenal": [
            {"opponent": "Chelsea", "date": "2024-12-15", "home": True},
            {"opponent": "Manchester City", "date": "2024-12-22", "home": False},
            {"opponent": "Liverpool", "date": "2024-12-29", "home": True},
        ]
    }
    
    team_fixtures = fixtures.get(team, [])[:num_fixtures]
    return json.dumps({"team": team, "fixtures": team_fixtures})


# Map tool names to implementations
TOOL_MAP: Dict[str, Callable] = {
    "get_active_roster": get_active_roster,
    "get_player_injury_status": get_player_injury_status,
    "get_upcoming_fixtures": get_upcoming_fixtures,
}


# =============================================================================
# AGENT LOOP
# =============================================================================

def execute_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Execute a tool and return the result as a string."""
    if tool_name not in TOOL_MAP:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})
    
    try:
        return TOOL_MAP[tool_name](**arguments)
    except Exception as e:
        return json.dumps({"error": str(e)})


def run_agent_loop(chat, max_iterations: int = 10) -> str:
    """
    Run the agent loop until the LLM is done reasoning.
    
    This loop:
    1. Calls chat.sample() to get a response
    2. If response contains tool_calls, executes them and appends results
    3. Continues until no more tool_calls (LLM is done)
    4. Returns the final content
    
    Args:
        chat: The xAI SDK chat object
        max_iterations: Safety limit to prevent infinite loops
        
    Returns:
        The final response content from the LLM
    """
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        print(f"\n{'─'*40}")
        print(f"🔄 Agent Loop - Iteration {iteration}")
        print(f"{'─'*40}")
        
        # Get response from LLM
        print("   📤 Calling chat.sample()...")
        response = chat.sample()
        
        # Debug: show response attributes
        print(f"   📥 Response type: {type(response).__name__}")
        attrs = [attr for attr in dir(response) if not attr.startswith('_')]
        print(f"   📥 Response attrs: {attrs}")
        
        # Check for tool calls
        tool_calls = getattr(response, 'tool_calls', None)
        
        if not tool_calls:
            # No tool calls - LLM is done reasoning
            print("   ✅ No tool calls - LLM finished reasoning")
            content = getattr(response, 'content', str(response))
            return content
        
        # Process each tool call
        print(f"   🔧 Found {len(tool_calls)} tool call(s)")
        
        for i, tool_call in enumerate(tool_calls):
            print(f"\n   Tool Call {i+1}:")
            
            # Extract tool call details (handle different SDK structures)
            tool_id = getattr(tool_call, 'id', getattr(tool_call, 'tool_call_id', None))

            if not tool_id:
                print(f"      ⚠️  No tool_id found, generating one")
                import uuid
                tool_id = str(uuid.uuid4())

            # Try different attribute patterns for tool name and arguments
            tool_name = None
            args_str = None

            # Pattern 1: OpenAI-style with function object
            if hasattr(tool_call, 'function'):
                func = tool_call.function
                tool_name = getattr(func, 'name', None)
                args_str = getattr(func, 'arguments', None)

            # Pattern 2: Direct attributes
            if not tool_name:
                tool_name = getattr(tool_call, 'name', None)
                args_str = getattr(tool_call, 'arguments', None)

            # Pattern 3: Check for other possible structures
            if not tool_name and hasattr(tool_call, 'tool'):
                tool_name = getattr(tool_call.tool, 'name', None)
                args_str = getattr(tool_call.tool, 'arguments', None)
            
            print(f"      ID: {tool_id}")
            print(f"      Name: {tool_name}")
            print(f"      Args: {args_str}")

            if not tool_name:
                print("      ⚠️  Could not extract tool name, skipping this tool call")
                continue

            if not tool_id:
                print("      ⚠️  Could not extract tool ID, skipping this tool call")
                continue
            
            # Parse arguments
            try:
                if isinstance(args_str, str):
                    arguments = json.loads(args_str)
                elif isinstance(args_str, dict):
                    arguments = args_str
                else:
                    print(f"      ⚠️  Unexpected args type: {type(args_str)}, using empty dict")
                    arguments = {}
            except json.JSONDecodeError as e:
                print(f"      ⚠️  JSON decode error: {e}, using empty dict")
                arguments = {}
            
            # Execute the tool
            print(f"      ⚡ Executing {tool_name}...")
            result = execute_tool_call(tool_name, arguments)
            print(f"      ✅ Result: {result[:100]}{'...' if len(result) > 100 else ''}")
            
            # Append tool result to chat
            print(f"      📤 Appending result to chat...")
            
            # Debug: Inspect available methods
            chat_methods = [m for m in dir(chat) if not m.startswith('_')]
            print(f"      📋 Chat object methods: {chat_methods}")
            
            # Check xai_sdk.chat module
            import xai_sdk.chat as chat_module
            chat_exports = [n for n in dir(chat_module) if not n.startswith('_')]
            print(f"      📋 xai_sdk.chat exports: {chat_exports}")
            
            result_appended = False

            # Method 1: tool_result might take a dict
            try:
                from xai_sdk.chat import tool_result
                # Inspect tool_result signature
                import inspect
                sig = inspect.signature(tool_result)
                print(f"      📋 tool_result signature: {sig}")
            except Exception as e:
                print(f"      ❌ Could not inspect tool_result: {e}")

            # Method 2: Try tool_result with just content (if it takes 1 arg)
            if not result_appended:
                try:
                    from xai_sdk.chat import tool_result
                    # Create a dict with all info
                    tr = tool_result(result)
                    # Maybe we need to set tool_call_id on it?
                    if hasattr(tr, 'tool_call_id'):
                        tr.tool_call_id = tool_id
                    chat.append(tr)
                    print(f"      ✅ Result appended via tool_result(content)")
                    result_appended = True
                except Exception as e:
                    print(f"      ❌ tool_result(content) failed: {e}")
            
            # Method 3: Check if there's a function_call_result or similar
            if not result_appended:
                try:
                    # Look for protobuf way
                    from xai_sdk.tools import chat_pb2
                    # List all message types
                    pb_types = [n for n in dir(chat_pb2) if n[0].isupper()][:30]
                    print(f"      📋 chat_pb2 types: {pb_types}")
                except Exception as e:
                    print(f"      ❌ protobuf inspection failed: {e}")

            if not result_appended:
                print(f"      ❌ All methods failed - need more research!")
                # Don't raise, let's see what we've learned
                return f"Tool result could not be appended. Tool ID: {tool_id}, Result: {result}"
        
        # Continue the loop - chat.sample() will be called again
        print("\n   🔄 Continuing agent loop...")
    
    print(f"\n⚠️  Max iterations ({max_iterations}) reached!")
    return "Max iterations reached"


# =============================================================================
# MAIN TEST
# =============================================================================

def test_agent_loop():
    """
    Test the agent loop with multiple tools.
    
    Ask a question that should require multiple tool calls:
    "Is Bukayo Saka available for Arsenal's next match?"
    
    Expected flow:
    1. LLM calls get_player_injury_status for Saka
    2. LLM calls get_upcoming_fixtures for Arsenal
    3. LLM synthesizes and responds
    """
    print("\n" + "="*60)
    print("Testing Agent Loop with Multiple Tools")
    print("="*60)
    
    from xai_sdk import Client
    from xai_sdk.chat import user, system
    
    try:
        client = Client(api_key=os.getenv('GROK_API_KEY'))
        print("✅ Client initialized")
        
        # Create custom tools using protobuf format
        custom_tools = create_custom_tools()
        
        # Create chat with all our custom tools
        chat = client.chat.create(
            model="grok-3-fast",
            tools=custom_tools
        )
        print(f"✅ Chat created with {len(custom_tools)} custom tools")
        
        # System message explaining available tools
        chat.append(system("""You are a sports analyst assistant. You have access to the following tools:
        
1. get_active_roster - Get the current roster for a team
2. get_player_injury_status - Check if a player is injured
3. get_upcoming_fixtures - Get upcoming matches for a team

Use these tools to answer questions about teams and players. Always check relevant data before answering."""))
        
        # User question that should trigger multiple tool calls
        question = "Is Bukayo Saka available for Arsenal's next match? Who would replace him if he's injured?"
        print(f"\n📝 User Question: {question}")
        
        chat.append(user(question))
        
        # Run the agent loop
        final_response = run_agent_loop(chat)
        
        print("\n" + "="*60)
        print("🎯 FINAL RESPONSE:")
        print("="*60)
        print(final_response)
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_inspect_response_structure():
    """
    Simple test to see what attributes are on the response object.
    """
    print("\n" + "="*60)
    print("Inspecting Response Structure")
    print("="*60)
    
    from xai_sdk import Client
    from xai_sdk.chat import user, system
    
    try:
        client = Client(api_key=os.getenv('GROK_API_KEY'))
        
        # Simple chat without tools first
        chat = client.chat.create(model="grok-3-fast")
        chat.append(user("Say hello in one word."))
        
        response = chat.sample()
        
        print("\n📥 Response Object Inspection:")
        print(f"   Type: {type(response)}")
        print(f"   Repr: {repr(response)[:200]}")
        print("\n   Attributes:")
        for attr in dir(response):
            if not attr.startswith('_'):
                try:
                    val = getattr(response, attr)
                    if not callable(val):
                        print(f"      {attr}: {type(val).__name__} = {str(val)[:50]}")
                except Exception:
                    print(f"      {attr}: <error accessing>")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_inspect_native_tools():
    """
    Inspect how native tools (web_search) are structured.
    """
    print("\n" + "="*60)
    print("Inspecting Native Tool Structure")
    print("="*60)
    
    from xai_sdk.tools import web_search, x_search, chat_pb2
    
    try:
        # Create tool instances
        ws = web_search()
        
        print("\n📋 web_search() tool:")
        print(f"   Type: {type(ws)}")
        print(f"   Repr: {repr(ws)[:500]}")
        print("\n   Attributes (non-callable):")
        for attr in dir(ws):
            if not attr.startswith('_'):
                try:
                    val = getattr(ws, attr)
                    if not callable(val):
                        print(f"      {attr}: {type(val).__name__} = {str(val)[:100]}")
                except Exception:
                    print(f"      {attr}: <error accessing>")
        
        # Inspect the Function field structure
        print("\n📋 Inspecting Tool.function field:")
        print(f"   ws.function type: {type(ws.function)}")
        print(f"   ws.function repr: {repr(ws.function)[:200]}")
        
        # Check Function attributes
        print("\n   Function field attributes:")
        for attr in dir(ws.function):
            if not attr.startswith('_') and attr[0].islower():
                try:
                    val = getattr(ws.function, attr)
                    if not callable(val):
                        print(f"      {attr}: {type(val).__name__}")
                except Exception:
                    pass
        
        # Try to create a custom tool using protobuf
        print("\n📋 Attempting to create custom Tool with function field:")
        try:
            custom_tool = chat_pb2.Tool()
            custom_tool.function.name = "get_active_roster"
            custom_tool.function.description = "Get the active roster for a team"
            custom_tool.function.parameters = json.dumps({
                "type": "object",
                "properties": {
                    "team": {"type": "string", "description": "Team name"},
                    "league": {"type": "string", "description": "League name"}
                },
                "required": ["team"]
            })
            print(f"   ✅ Created custom tool!")
            print(f"   Type: {type(custom_tool)}")
            print(f"   Repr: {repr(custom_tool)[:300]}")
        except Exception as e:
            print(f"   ❌ Failed to create custom tool: {e}")
            
            # Try alternative approach - check chat_pb2 for Tool and Function classes
            print("\n📋 Checking chat_pb2 contents:")
            for name in dir(chat_pb2):
                if not name.startswith('_') and name[0].isupper():
                    print(f"      {name}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run tests."""
    print("="*60)
    print("xAI SDK Custom Tool Testing - Agent Loop Pattern")
    print("="*60)
    
    # Check for API key
    if not os.getenv('GROK_API_KEY'):
        print("❌ GROK_API_KEY not set in environment")
        return
    
    print("✅ API key found")
    
    # First, inspect native tools to understand the format
    print("\n" + "─"*60)
    print("STEP 1: Inspect native tool structure")
    print("─"*60)
    test_inspect_native_tools()
    
    # Inspect response structure
    print("\n" + "─"*60)
    print("STEP 2: Inspect response structure")
    print("─"*60)
    test_inspect_response_structure()
    
    # Then test the full agent loop
    print("\n" + "─"*60)
    print("STEP 3: Test agent loop with tools")
    print("─"*60)
    test_agent_loop()
    
    print("\n" + "="*60)
    print("Testing complete!")
    print("="*60)


if __name__ == "__main__":
    main()

