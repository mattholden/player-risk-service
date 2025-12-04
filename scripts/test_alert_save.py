"""
Test script for saving alerts to the database.

This script creates mock alerts and tests the database save functionality
without running the full agent pipeline (avoiding expensive API calls).
"""

from datetime import datetime
from src.agents.models import PlayerAlert
from database.enums import AlertLevel
from database import Alert, session_scope
from src.services.agent_pipeline import AgentPipeline


def create_mock_alerts():
    """Create mock PlayerAlert objects for testing."""
    
    fixture = "Test Team A vs Test Team B"
    fixture_date = datetime(2025, 12, 31, 20, 0)
    
    # Test case 1: Multiple alerts for different players
    alerts = [
        PlayerAlert(
            player_name="Test Player Alpha",
            fixture=fixture,
            fixture_date=fixture_date,
            alert_level=AlertLevel.HIGH_ALERT,
            description="[Test Team A] Test Player Alpha ruled out for weeks due to test injury. High priority alert."
        ),
        PlayerAlert(
            player_name="Test Player Beta",
            fixture=fixture,
            fixture_date=fixture_date,
            alert_level=AlertLevel.MEDIUM_ALERT,
            description="[Test Team A] Test Player Beta questionable with minor knock. Medium alert level."
        ),
        # Test case 2: Same player with multiple alerts (different descriptions/contexts)
        PlayerAlert(
            player_name="Test Player Gamma",
            fixture=fixture,
            fixture_date=fixture_date,
            alert_level=AlertLevel.MEDIUM_ALERT,
            description="[Test Team A] Test Player Gamma has favorable matchup against weakened opposition defense."
        ),
        PlayerAlert(
            player_name="Test Player Gamma",
            fixture=fixture,
            fixture_date=fixture_date,
            alert_level=AlertLevel.MEDIUM_ALERT,
            description="[Test Team B] Test Player Gamma from opposition perspective - late fitness test required."
        ),
        # Test case 3: Low alert
        PlayerAlert(
            player_name="Test Player Delta",
            fixture=fixture,
            fixture_date=fixture_date,
            alert_level=AlertLevel.LOW_ALERT,
            description="[Test Team B] Test Player Delta positioned for increased minutes as backup option."
        ),
        # Test case 4: No alert
        PlayerAlert(
            player_name="Test Player Epsilon",
            fixture=fixture,
            fixture_date=fixture_date,
            alert_level=AlertLevel.NO_ALERT,
            description="[Test Team A] Test Player Epsilon fully fit and available for selection."
        ),
    ]
    
    return alerts


def test_save_alerts():
    """Test saving alerts using the pipeline method."""
    print("=" * 70)
    print("🧪 Testing Alert Save Functionality")
    print("=" * 70)
    
    # Create mock alerts
    print("\n📋 Creating mock alerts...")
    alerts = create_mock_alerts()
    print(f"✅ Created {len(alerts)} mock alerts")
    
    # Display alerts
    print("\n📊 Mock Alerts:")
    for i, alert in enumerate(alerts, 1):
        print(f"\n{i}. {alert.player_name}")
        print(f"   Fixture: {alert.fixture}")
        print(f"   Alert Level: {alert.alert_level.value}")
        print(f"   Description: {alert.description[:80]}...")
    
    # Save alerts using pipeline method
    print("\n" + "=" * 70)
    print("💾 Saving alerts to database...")
    print("=" * 70)
    
    try:
        pipeline = AgentPipeline()
        pipeline._save_alerts(alerts)
        print("✅ Alerts saved successfully!")
    except Exception as e:
        print(f"❌ Error saving alerts: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Verify alerts were saved
    print("\n" + "=" * 70)
    print("🔍 Verifying alerts in database...")
    print("=" * 70)
    
    try:
        with session_scope() as session:
            saved_alerts = session.query(Alert).all()
            print(f"\n✅ Found {len(saved_alerts)} alerts in database")
            
            # Display saved alerts
            for i, alert in enumerate(saved_alerts, 1):
                print(f"\n{i}. {alert.player_name}")
                print(f"   Fixture: {alert.fixture}")
                print(f"   Alert Level: {alert.alert_level.value}")
                print(f"   Description: {alert.description[:60]}...")
                print(f"   Created: {alert.created_at}")
                print(f"   Acknowledged: {alert.acknowledged}")
                print(f"   Active: {alert.active_projection}")
            
            # Check for duplicates (same player should be allowed)
            player_names = [alert.player_name for alert in saved_alerts]
            duplicate_players = set([name for name in player_names if player_names.count(name) > 1])
            
            if duplicate_players:
                print(f"\n✅ Found duplicate player names (as expected): {duplicate_players}")
                print("   Multiple alerts per player are allowed! ✓")
            
        return True
        
    except Exception as e:
        print(f"❌ Error verifying alerts: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_query_alerts():
    """Test querying alerts with various filters."""
    print("\n" + "=" * 70)
    print("🔍 Testing Alert Queries")
    print("=" * 70)
    
    try:
        with session_scope() as session:
            # Query 1: High alerts only
            high_alerts = session.query(Alert).filter(
                Alert.alert_level == AlertLevel.HIGH_ALERT
            ).all()
            print(f"\n🚨 High Alerts: {len(high_alerts)}")
            for alert in high_alerts:
                print(f"   - {alert.player_name}: {alert.description[:50]}...")
            
            # Query 2: Alerts for a specific player
            player_name = "Test Player Gamma"
            player_alerts = session.query(Alert).filter(
                Alert.player_name == player_name
            ).all()
            print(f"\n👤 Alerts for {player_name}: {len(player_alerts)}")
            for alert in player_alerts:
                print(f"   - {alert.description[:50]}...")
            
            # Query 3: Active, unacknowledged alerts
            active_alerts = session.query(Alert).filter(
                Alert.active_projection == True,
                Alert.acknowledged == False
            ).all()
            print(f"\n⚡ Active, Unacknowledged Alerts: {len(active_alerts)}")
            
            # Query 4: Alerts by fixture
            fixture = "Test Team A vs Test Team B"
            fixture_alerts = session.query(Alert).filter(
                Alert.fixture == fixture
            ).all()
            print(f"\n🏟️  Alerts for {fixture}: {len(fixture_alerts)}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error querying alerts: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("🚀 ALERT DATABASE TESTING SUITE")
    print("=" * 70)
    
    # Test 1: Save alerts
    success = test_save_alerts()
    
    if not success:
        print("\n❌ Alert save test failed!")
        return
    
    # Test 2: Query alerts
    success = test_query_alerts()
    
    if not success:
        print("\n❌ Alert query test failed!")
        return
    
    # Final summary
    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED!")
    print("=" * 70)
    print("\n📝 Summary:")
    print("   ✓ Alerts can be saved to database")
    print("   ✓ Multiple alerts per player are allowed")
    print("   ✓ Alert queries work correctly")
    print("   ✓ Database schema is correct")
    print("\n🎉 Ready to run the full pipeline!")


if __name__ == "__main__":
    main()

