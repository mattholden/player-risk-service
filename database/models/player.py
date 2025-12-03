"""
Player database model.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, Index, Boolean, Text
from database.base import Base
from database.enums import AlertLevel


class Player(Base):
    """
    Player model for tracking sports players and their risk assessments.
    
    Attributes:
        id: Primary key
        name: Player's full name
        team: Current team
        position: player's position
        fixture: fixture name
        fixture_date: fixture date
        acknowledged: game ops team has acknowledged the player's risk and made adjustments
        active_projection: only active before a fixture is played
        risk_tag: current risk level (NO_RISK, LOW, MEDIUM, HIGH, UNKNOWN)
        risk_explanation: explanation of the risk level
        last_risk_update: when risk was last assessed
        created_at: when player was added to system
    """
    
    __tablename__ = 'players'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Player information
    name = Column(String(200), nullable=False, unique=True)
    team = Column(String(200), nullable=False)
    position = Column(String(10), nullable=True)
    fixture = Column(String(200), nullable=False)
    fixture_date = Column(DateTime, nullable=False)
    acknowledged = Column(Boolean, nullable=False, default=False) 
    active_projection = Column(Boolean, nullable=False, default=True)
    
    # Risk assessment
    risk_tag = Column(
        SQLEnum(AlertLevel),
        nullable=False,
        default=AlertLevel.NO_ALERT,
        index=True  # Fast queries by risk level
    )
    risk_explanation = Column(Text, nullable=True)
    last_risk_update = Column(DateTime, nullable=True)
    
    # Tracking timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Indexes for faster queries
    __table_args__ = (
        Index('idx_risk_tag', 'risk_tag'),
        Index('idx_team', 'team'),
        Index('idx_fixture_date', 'fixture_date'),  # For querying upcoming fixtures
        # Note: 'name' already has unique=True which creates an index automatically
    )
    
    def __repr__(self):
        """String representation of Player."""
        return f"<Player(id={self.id}, name='{self.name}', team='{self.team}', risk={self.risk_tag.value})>"
    
    def to_dict(self):
        """
        Convert player to dictionary format.
        
        Returns:
            dict: Player data as dictionary
        """
        return {
            'id': self.id,
            'name': self.name,
            'team': self.team,
            'position': self.position,
            'fixture': self.fixture,
            'fixture_date': self.fixture_date.isoformat() if self.fixture_date else None,
            'risk_tag': self.risk_tag.value,
            'risk_explanation': self.risk_explanation,
            'last_risk_update': self.last_risk_update.isoformat() if self.last_risk_update else None,
            'acknowledged': self.acknowledged,
            'active_projection': self.active_projection,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
