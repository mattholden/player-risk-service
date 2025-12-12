"""
Test Roster Tool Integration

This script tests:
1. The ActiveRosterTool with the tools infrastructure
2. Integration with xAI SDK
3. Agent loop execution with real LLM

Run from project root:
    python -m scripts.test_roster_tool
"""

import os
from dotenv import load_dotenv

load_dotenv()


def test_tool_infrastructure():
    """Test the basic tool infrastructure without LLM."""
    print("\n" + "="*60)
    print("Testing Tool Infrastructure")
    print("="*60)
    
    from src.tools import tool_registry, ActiveRosterTool
    
    # Clear and register tool
    tool_registry.clear()
    tool_registry.register(ActiveRosterTool())
    
    print(f"\n✅ Registry: {tool_registry}")
    print(f"   Registered tools: {tool_registry.get_tool_names()}")
    
    # Test protobuf conversion
    protobufs = tool_registry.get_all_protobufs()
    print(f"   Protobuf tools: {len(protobufs)}")
    for pb in protobufs:
        print(f"      - {pb.function.name}")
    
    # Test direct execution
    print("\n📋 Testing direct tool execution:")
    result = tool_registry.execute("get_active_roster", {
        "team": "Arsenal",
        "league": "Premier League"
    })
    print(f"   Result: {result[:200]}...")
    
    return True


def test_with_llm():
    """Test the tool with actual LLM integration."""
    print("\n" + "="*60)
    print("Testing Tool with LLM (via GrokClient.chat_with_tools)")
    print("="*60)
    
    from src.clients.grok_client import GrokClient
    from src.tools import tool_registry, ActiveRosterTool
    
    # Setup
    grok_client = GrokClient()
    print("✅ GrokClient initialized")
    
    # Register tool
    tool_registry.clear()
    tool_registry.register(ActiveRosterTool())
    print(f"✅ Tools registered: {tool_registry.get_tool_names()}")
    
    # Build messages
    messages = [
        {
            "role": "system",
            "content": """You are a sports analyst assistant. You have access to tools that can retrieve team rosters.

When asked about a team's players, use the get_active_roster tool to fetch the current roster.
Always use the tool before answering questions about team compositions."""
        },
        {
            "role": "user",
            "content": "Who are the players on Arsenal's roster in the Premier League? List them by position."
        }
    ]
    
    print(f"\n📝 Question: {messages[1]['content']}")
    
    # Use the new chat_with_tools method
    print("\n🔄 Running chat_with_tools...")
    try:
        response = grok_client.chat_with_tools(
            messages=messages,
            tool_registry=tool_registry,
            use_web_search=False,
            use_x_search=False,
            verbose=True
        )
        
        print("\n" + "="*60)
        print("🎯 FINAL RESPONSE:")
        print("="*60)
        print(response.get('content', 'No content'))
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("="*60)
    print("Roster Tool Integration Test")
    print("="*60)
    
    # Check for API key
    if not os.getenv('GROK_API_KEY'):
        print("❌ GROK_API_KEY not set")
        return
    
    print("✅ API key found")
    
    # Test 1: Infrastructure
    test_tool_infrastructure()
    
    # Test 2: LLM integration
    test_with_llm()
    
    print("\n" + "="*60)
    print("Testing complete!")
    print("="*60)


if __name__ == "__main__":
    main()

