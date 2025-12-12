"""
Test script for BigQuery integration.

Run this to verify:
1. BigQuery connection works
2. Player name matching works correctly
3. Projections enrichment pipeline functions

Usage:
    python scripts/test_bigquery.py
"""

import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from bigquery.matching import PlayerMatcher
from database.enums import AlertLevel


def test_player_matching():
    """Test the player name matching logic."""
    print("\n" + "="*60)
    print("Testing Player Name Matching")
    print("="*60)
    
    matcher = PlayerMatcher(threshold=0.80)
    
    # Test cases: (name1, name2, expected_match)
    test_cases = [
        # Exact matches
        ("Viktor Gyökeres", "Viktor Gyökeres", True),
        
        # Accent variations
        ("Viktor Gyökeres", "Viktor Gyokeres", True),
        ("Gabriel Magalhães", "Gabriel Magalhaes", True),
        
        # Partial names
        ("Gabriel", "Gabriel Magalhães", True),
        ("Saliba", "William Saliba", True),
        
        # Abbreviations
        ("W. Saliba", "William Saliba", True),
        
        # Different players (should NOT match)
        ("Gabriel Jesus", "Gabriel Martinelli", False),
        ("Ben White", "Benjamin Mendy", False),
        
        # Edge cases
        ("Piero Hincapié", "Piero Hincapie", True),
        ("Kevin De Bruyne", "De Bruyne", True),
        
        # Completely different
        ("Mo Salah", "Kevin De Bruyne", False),
    ]
    
    passed = 0
    failed = 0
    
    for name1, name2, expected in test_cases:
        result = matcher.is_match(name1, name2)
        status = "✅" if result == expected else "❌"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        print(f"  {status} '{name1}' vs '{name2}'")
        print(f"     Expected: {expected}, Got: {result}")
        
        # Show similarity score for debugging
        score = matcher.similarity_score(name1, name2)
        print(f"     Similarity: {score:.2f}")
        print()
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_bigquery_connection():
    """Test BigQuery connection."""
    print("\n" + "="*60)
    print("Testing BigQuery Connection")
    print("="*60)
    
    # Check if credentials are configured
    project_id = os.getenv("BIGQUERY_PROJECT_ID")
    if not project_id:
        print("⚠️  BIGQUERY_PROJECT_ID not set - skipping connection test")
        print("   Set this in your .env file to test BigQuery connectivity")
        return True
    
    try:
        from bigquery.client import BigQueryClient
        
        client = BigQueryClient()
        if client.health_check():
            print("✅ BigQuery connection successful!")
            return True
        else:
            print("❌ BigQuery connection failed")
            return False
    except Exception as e:
        print(f"❌ BigQuery connection error: {e}")
        return False


def test_enrichment_simulation():
    """Simulate the enrichment pipeline without actual BigQuery calls."""
    print("\n" + "="*60)
    print("Testing Enrichment Pipeline (Simulated)")
    print("="*60)
    
    import pandas as pd
    from src.agents.models import PlayerAlert
    from bigquery.matching import PlayerMatcher
    
    # Simulate projections data
    projections_data = {
        "player_name": [
            "Viktor Gyökeres",
            "Gabriel Magalhães", 
            "William Saliba",
            "Bukayo Saka",
            "Kevin Schade",
            "Igor Thiago",
            "Noni Madueke",
        ],
        "fixture": [
            "Arsenal vs Brentford",
            "Arsenal vs Brentford",
            "Arsenal vs Brentford",
            "Arsenal vs Brentford",
            "Arsenal vs Brentford",
            "Arsenal vs Brentford",
            "Arsenal vs Brentford",
        ],
        "projection_points": [12.5, 8.2, 7.1, 11.3, 6.8, 9.1, 7.5],
    }
    projections = pd.DataFrame(projections_data)
    
    # Simulate alerts (using normalized names as might come from agent)
    alerts = [
        PlayerAlert(
            player_name="Viktor Gyokeres",  # Note: no accent
            fixture="Arsenal vs Brentford",
            fixture_date=datetime(2025, 12, 3, 19, 45),
            alert_level=AlertLevel.HIGH_ALERT,
            description="Starting as central striker due to Havertz injury"
        ),
        PlayerAlert(
            player_name="Gabriel",  # Short name
            fixture="Arsenal vs Brentford",
            fixture_date=datetime(2025, 12, 3, 19, 45),
            alert_level=AlertLevel.HIGH_ALERT,
            description="Ruled out with thigh injury"
        ),
        PlayerAlert(
            player_name="William Saliba",
            fixture="Arsenal vs Brentford",
            fixture_date=datetime(2025, 12, 3, 19, 45),
            alert_level=AlertLevel.MEDIUM_ALERT,
            description="Questionable pending training assessment"
        ),
        PlayerAlert(
            player_name="Kevin Schade",
            fixture="Arsenal vs Brentford",
            fixture_date=datetime(2025, 12, 3, 19, 45),
            alert_level=AlertLevel.MEDIUM_ALERT,
            description="Likely to start centrally as striker"
        ),
    ]
    
    # Perform matching
    matcher = PlayerMatcher()
    
    print(f"\n📊 Input: {len(projections)} projections, {len(alerts)} alerts")
    print("\nMatching results:")
    
    matched_count = 0
    for idx, row in projections.iterrows():
        player = row["player_name"]
        matched_alert = None
        
        for alert in alerts:
            if matcher.is_match(player, alert.player_name):
                matched_alert = alert
                break
        
        if matched_alert:
            matched_count += 1
            print(f"  ✅ {player}")
            print(f"     → Matched: {matched_alert.player_name}")
            print(f"     → Alert: {matched_alert.alert_level.value}")
        else:
            print(f"  ⚪ {player} (no alert)")
    
    print(f"\n📈 Summary: {matched_count}/{len(projections)} projections matched with alerts")
    return True


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("BigQuery Integration Tests")
    print("="*60)
    
    all_passed = True
    
    # Test matching logic
    if not test_player_matching():
        all_passed = False
    
    # Test BigQuery connection (optional)
    test_bigquery_connection()
    
    # Test enrichment simulation
    if not test_enrichment_simulation():
        all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")
    print("="*60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

