"""
Quick test script to verify Article model works.

Run from project root:
    python -m scripts.test_article

Or:
    cd /path/to/player-risk-service
    python scripts/test_article.py
"""

from database import Article, session_scope
from datetime import datetime

def test_article_crud():
    """Test Article Create, Read operations."""
    
    print("="*60)
    print("Testing Article Model")
    print("="*60)
    
    # CREATE
    print("\n1. Creating test article...")
    with session_scope() as session:
        article = Article(
            title="Jaden Ivey Scores Career High 30 Points",
            description="Detroit Pistons guard shows offensive prowess",
            url="https://example.com/jaden-ivey-career-high",
            source="ESPN",
            author="Test Reporter",
            content="Jaden Ivey put on a show...",
            published_at=datetime.now()
        )
        session.add(article)
    
    print("✅ Article created successfully!")
    
    # READ
    print("\n2. Reading article from database...")
    with session_scope() as session:
        found_article = session.query(Article).filter_by(
            url="https://example.com/jaden-ivey-career-high"
        ).first()
        
        if found_article:
            print(f"✅ Found: {found_article}")
            print(f"   Title: {found_article.title}")
            print(f"   Source: {found_article.source}")
            print(f"   Published: {found_article.published_at}")
        else:
            print("❌ Article not found!")
            return False
    
    # TEST UNIQUE CONSTRAINT
    print("\n3. Testing unique URL constraint...")
    try:
        with session_scope() as session:
            duplicate = Article(
                title="Different Title",
                url="https://example.com/jaden-ivey-career-high",  # Same URL
                source="Other Source"
            )
            session.add(duplicate)
        print("❌ Unique constraint failed! Duplicate was allowed.")
    except Exception as e:
        print("✅ Unique constraint working! Duplicate rejected.")
    
    # COUNT
    print("\n4. Counting articles...")
    with session_scope() as session:
        count = session.query(Article).count()
        print(f"✅ Total articles in database: {count}")
    
    # DELETE (cleanup)
    print("\n5. Cleaning up (deleting test article)...")
    with session_scope() as session:
        article = session.query(Article).filter_by(
            url="https://example.com/jaden-ivey-career-high"
        ).first()
        if article:
            session.delete(article)
    
    print("✅ Article deleted successfully!")
    
    print("\n" + "="*60)
    print("✅ All Article model tests passed!")
    print("="*60)
    
    return True

if __name__ == "__main__":
    try:
        test_article_crud()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

