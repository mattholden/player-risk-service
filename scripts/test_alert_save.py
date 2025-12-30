"""
Test script for the AlertService.

Tests saving, querying, and managing alerts through the new AlertService
without running the full agent pipeline (avoiding expensive API calls).
"""

from datetime import datetime, timedelta
from src.agents.models import PlayerAlert
from database.enums import AlertLevel
from database import AlertService


def create_mock_alerts():
    """Create mock PlayerAlert objects for testing."""
    
    fixture = "Test Team A vs Test Team B"
    fixture_date = datetime(1900, 12, 31, 20, 0)
    
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
        PlayerAlert(
            player_name="Test Player Delta",
            fixture=fixture,
            fixture_date=fixture_date,
            alert_level=AlertLevel.LOW_ALERT,
            description="[Test Team B] Test Player Delta positioned for increased minutes as backup option."
        ),
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
    """Test saving alerts using AlertService."""
    print("=" * 70)
    print("🧪 Test 1: Save Alerts via AlertService")
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
    
    # Save alerts using AlertService
    print("\n" + "-" * 70)
    print("💾 Saving alerts via AlertService...")
    
    try:
        service = AlertService()
        saved_count = service.save_alerts(alerts)
        print(f"✅ AlertService.save_alerts() returned: {saved_count}")
        return True
    except Exception as e:
        print(f"❌ Error saving alerts: {e}")
        import traceback
        traceback.print_exc()
        return False
    

def test_query_by_fixture():
    """Test querying alerts by fixture."""
    print("\n" + "=" * 70)
    print("🧪 Test 2: Query Alerts by Fixture")
    print("=" * 70)
    
    try:
        service = AlertService()
        fixture = "Test Team A vs Test Team B"
        
        alerts = service.get_alerts_for_fixture(fixture)
        print(f"\n🏟️  Alerts for '{fixture}': {len(alerts)}")
        
        for alert in alerts:
            print(f"   • {alert.player_name} ({alert.alert_level.value})")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_query_multiple_fixtures():
    """Test querying alerts for multiple fixtures."""
    print("\n" + "=" * 70)
    print("🧪 Test 3: Query Alerts for Multiple Fixtures")
    print("=" * 70)
    
    try:
        service = AlertService()
        fixtures = ["Test Team A vs Test Team B", "Nonexistent Fixture"]
        
        alerts = service.get_alerts_for_fixtures(fixtures)
        print(f"\n📋 Alerts for {len(fixtures)} fixtures: {len(alerts)}")
        
        for alert in alerts:
            print(f"   • {alert.player_name} - {alert.fixture}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_query_active_alerts():
    """Test querying active alerts."""
    print("\n" + "=" * 70)
    print("🧪 Test 4: Query Active Alerts")
    print("=" * 70)
    
    try:
        service = AlertService()
        
        alerts = service.get_active_alerts()
        print(f"\n⚡ Active alerts: {len(alerts)}")
            
        # Group by alert level
        from collections import Counter
        levels = Counter(a.alert_level.value for a in alerts)
        print("\n   By level:")
        for level, count in sorted(levels.items()):
            print(f"      {level}: {count}")
            
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_query_by_level():
    """Test querying alerts by alert level."""
    print("\n" + "=" * 70)
    print("🧪 Test 5: Query Alerts by Level")
    print("=" * 70)
    
    try:
        service = AlertService()
        
        # Query high and medium alerts
        levels = [AlertLevel.HIGH_ALERT, AlertLevel.MEDIUM_ALERT]
        alerts = service.get_alerts_by_level(levels)
        
        print(f"\n🚨 High/Medium alerts: {len(alerts)}")
        for alert in alerts:
            print(f"   • {alert.player_name} ({alert.alert_level.value})")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_query_alerts_since():
    """Test querying alerts since a date."""
    print("\n" + "=" * 70)
    print("🧪 Test 6: Query Alerts Since Date")
    print("=" * 70)
    
    try:
        service = AlertService()
        
        # Query alerts from the last hour
        since = datetime.now() - timedelta(hours=1)
        alerts = service.get_alerts_since(since)
        
        print(f"\n📅 Alerts in last hour: {len(alerts)}")
        for alert in alerts[:5]:  # Show first 5
            print(f"   • {alert.player_name} - {alert.created_at}")
        
        if len(alerts) > 5:
            print(f"   ... and {len(alerts) - 5} more")
            
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_deactivate_fixture():
    """Test deactivating alerts for a fixture."""
    print("\n" + "=" * 70)
    print("🧪 Test 7: Deactivate Fixture Alerts")
    print("=" * 70)
    
    try:
        service = AlertService()
        fixture = "Test Team A vs Test Team B"
        
        # Check active count before
        before = service.get_alerts_for_fixture(fixture)
        print(f"\n📊 Active alerts before: {len(before)}")
        
        # Deactivate
        deactivated = service.deactivate_fixture_alerts(fixture)
        print(f"🔒 Deactivated: {deactivated}")
        
        # Check active count after
        after = service.get_alerts_for_fixture(fixture)
        print(f"📊 Active alerts after: {len(after)}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all AlertService tests."""
    print("\n" + "=" * 70)
    print("🚀 ALERT SERVICE TEST SUITE")
    print("=" * 70)
    
    tests = [
        ("Save Alerts", test_save_alerts),
        ("Query by Fixture", test_query_by_fixture),
        ("Query Multiple Fixtures", test_query_multiple_fixtures),
        ("Query Active Alerts", test_query_active_alerts),
        ("Query by Level", test_query_by_level),
        ("Query Since Date", test_query_alerts_since),
        ("Deactivate Fixture", test_deactivate_fixture),
    ]
    
    results = []
    for name, test_fn in tests:
        try:
            success = test_fn()
            results.append((name, success))
        except Exception as e:
            print(f"❌ Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, success in results if success)
    failed = len(results) - passed
    
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"   {status} {name}")
    
    print(f"\n   Total: {passed}/{len(results)} passed")
    
    if failed == 0:
        print("\n🎉 All tests passed! AlertService is working correctly.")
    else:
        print(f"\n⚠️  {failed} test(s) failed.")


if __name__ == "__main__":
    main()
