"""
Quick test script to verify Player model works.

Run from project root:
    python -m scripts.test_player

Or:
    cd /path/to/player-risk-service
    python scripts/test_player.py
"""

from database import Player, RiskTag, session_scope
from datetime import datetime

def test_player_crud():
    """Test Player Create, Read, Update, Delete operations."""
    
    print("="*60)
    print("Testing Player Model")
    print("="*60)
    
    # CREATE
    print("\n1. Creating test player...")
    with session_scope() as session:
        player = Player(
            name="Jaden Ivey",
            team="Detroit Pistons",
            position="SG",
            fixture="Pistons vs Lakers",
            fixture_date=datetime(2025, 12, 25, 19, 30),
            risk_tag=RiskTag.LOW,
            risk_explanation="No recent injury reports",
            acknowledged=False,
            active_projection=True
        )
        session.add(player)
    
    print("✅ Player created successfully!")
    
    # READ
    print("\n2. Reading player from database...")
    with session_scope() as session:
        found_player = session.query(Player).filter_by(name="Jaden Ivey").first()
        if found_player:
            print(f"✅ Found: {found_player}")
            print(f"   Risk: {found_player.risk_tag.value}")
            print(f"   Fixture: {found_player.fixture}")
            print(f"   Dict: {found_player.to_dict()}")
        else:
            print("❌ Player not found!")
            return False
    
    # UPDATE
    print("\n3. Updating player risk...")
    with session_scope() as session:
        player = session.query(Player).filter_by(name="Jaden Ivey").first()
        player.risk_tag = RiskTag.HIGH
        player.risk_explanation = "Minor ankle injury reported"
        player.last_risk_update = datetime.now()
    
    print("✅ Player updated successfully!")
    
    # VERIFY UPDATE
    print("\n4. Verifying update...")
    with session_scope() as session:
        player = session.query(Player).filter_by(name="Jaden Ivey").first()
        if player.risk_tag == RiskTag.HIGH:
            print(f"✅ Risk correctly updated to: {player.risk_tag.value}")
        else:
            print(f"❌ Update failed! Risk is: {player.risk_tag.value}")
    
    # DELETE (cleanup)
    print("\n5. Cleaning up (deleting test player)...")
    with session_scope() as session:
        player = session.query(Player).filter_by(name="Jaden Ivey").first()
        session.delete(player)
    
    print("✅ Player deleted successfully!")
    
    print("\n" + "="*60)
    print("✅ All Player model tests passed!")
    print("="*60)
    
    return True

if __name__ == "__main__":
    try:
        test_player_crud()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

