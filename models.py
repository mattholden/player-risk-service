"""
Database models for the player risk service.

This module defines SQLAlchemy ORM models that map to database tables.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Article(Base):
    """
    Article model for storing news articles from NewsAPI.
    
    Attributes:
        id: Primary key
        title: Article title
        description: Brief description/summary
        url: Article URL (unique - prevents duplicate articles)
        published_at: When the article was published
        source: Name of the news source
        author: Article author (nullable)
        content: Article content snippet (nullable)
        created_at: When we saved this article to our database
        updated_at: When we last updated this article
    """
    
    __tablename__ = 'articles'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Article metadata
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    url = Column(String(2048), nullable=False, unique=True)  # Unique to prevent duplicates
    published_at = Column(DateTime, nullable=True)
    source = Column(String(200), nullable=True)
    author = Column(String(200), nullable=True)
    content = Column(Text, nullable=True)
    
    # Tracking timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes for faster queries
    __table_args__ = (
        Index('idx_published_at', 'published_at'),
        Index('idx_source', 'source'),
        Index('idx_created_at', 'created_at'),
    )
    
    def __repr__(self):
        """String representation of Article."""
        return f"<Article(id={self.id}, title='{self.title[:50]}...', source='{self.source}')>"
    
    def to_dict(self):
        """
        Convert article to dictionary format.
        
        Returns:
            dict: Article data as dictionary
        """
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'url': self.url,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'source': self.source,
            'author': self.author,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

