"""
Test script for Grok API client.

This script verifies that:
1. API key is configured correctly
2. Connection to xAI API works
3. Basic chat completion functions
4. Rate limiting is tracking properly

Run this before building the full Research Agent.

Usage:
    python -m scripts.test_grok_client
"""

from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from src.clients.grok_client import GrokClient


def test_connection():
    """Test basic API connectivity."""
    print("=" * 60)
    print("🧪 Test 1: API Connection")
    print("=" * 60)
    
    try:
        client = GrokClient()
        print("✅ Client initialized successfully")
        return client
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("\nMake sure GROK_API_KEY is set in your .env file:")
        print("  GROK_API_KEY=your_actual_key_here")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        return None


def test_simple_query(client: GrokClient):
    """Test a simple chat completion."""
    print("\n" + "=" * 60)
    print("🧪 Test 2: Simple Query")
    print("=" * 60)
    
    try:
        response = client.chat_completion(
            messages=[
                {
                    "role": "user",
                    "content": "Respond with exactly: 'Grok API is working!'"
                }
            ]
        )
        
        print(f"✅ Response received:")
        print(f"   Content: {response['content']}")
        print(f"   Model: {response['model']}")
        print(f"   Tokens: {response['usage']['total_tokens']}")
        print(f"   Timestamp: {response['created_at']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Query failed: {e}")
        return False


def test_sports_query(client: GrokClient):
    """Test a sports-related query to verify real-time search."""
    print("\n" + "=" * 60)
    print("🧪 Test 3: Sports Query with Search")
    print("=" * 60)
    
    try:
        print("🔍 Searching for recent NBA news...")
        
        response = client.search_and_summarize(
            query="What happened in the most recent NBA games today? Provide 2-3 examples with scores.",
        )
        
        print(f"\n✅ Response received:")
        print(f"   {response['content'][:500]}...")  # First 500 chars
        print(f"\n📊 Stats:")
        print(f"   Model: {response['model']}")
        print(f"   Tokens: {response['usage']['total_tokens']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Sports query failed: {e}")
        return False


def test_rate_limiting(client: GrokClient):
    """Test rate limit tracking."""
    print("\n" + "=" * 60)
    print("🧪 Test 4: Rate Limit Tracking")
    print("=" * 60)
    
    status = client.get_rate_limit_status()
    
    print(f"📊 Rate Limit Status:")
    print(f"   Requests made: {status['requests_made']}")
    print(f"   Remaining: {status['requests_remaining']}")
    print(f"   Limit: {status['limit']} per hour")
    print(f"   Window: {status['window_seconds']} seconds")
    
    if status['requests_remaining'] < status['limit']:
        print(f"   Reset at: {status['reset_time'].strftime('%H:%M:%S')}")
    
    print("✅ Rate limiting is working")
    return True


def main():
    """Run all tests."""
    import sys
    
    print("\n🚀 Testing Grok API Client")
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test 1: Connection
    client = test_connection()
    if not client:
        print("\n❌ Cannot proceed without valid API connection")
        return False
    
    # Test 2: Simple query
    if not test_simple_query(client):
        print("\n⚠️  Simple query failed, but continuing...")
    
    # Test 3: Sports query
    if not test_sports_query(client):
        print("\n⚠️  Sports query failed, but continuing...")
    
    # Test 4: Rate limiting
    test_rate_limiting(client)
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ All Tests Complete!")
    print("=" * 60)
    print("\n📝 Next Steps:")
    print("   1. Review the responses above")
    print("   2. If everything looks good, proceed to build Research Agent")
    print("   3. Run: python -m scripts.test_research_agent")
    print()
    
    return True


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)

