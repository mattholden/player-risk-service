"""
Player database model.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, Index, Boolean, Text
from database.base import Base
from database.enums import AlertLevel


class Alert(Base):
    """
    Alert model for tracking player alerts.
    
    Attributes:
        id: Primary key
        name: Player's full name
        fixture: fixture name
        fixture_date: fixture date
        acknowledged: game ops team has acknowledged the player's risk and made adjustments
        active_projection: only active before a fixture is played
        alert_level: current alert level (NO_ALERT, LOW, MEDIUM, HIGH)
        description: explanation of the alert level
        last_alert_update: when alert was last assessed
        created_at: when alert was added to system
    """
    
    __tablename__ = 'alerts'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Alert information
    player_name = Column(String(200), nullable=False)
    fixture = Column(String(200), nullable=False)
    fixture_date = Column(DateTime, nullable=False)
    acknowledged = Column(Boolean, nullable=False, default=False) 
    active_projection = Column(Boolean, nullable=False, default=True)
    
    # Alert assessment
    alert_level = Column(
        SQLEnum(AlertLevel),
        nullable=False,
        default=AlertLevel.NO_ALERT,
        index=True  # Fast queries by risk level
    )
    description = Column(Text, nullable=True)
    last_alert_update = Column(DateTime, nullable=True)
    
    # Tracking timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Indexes for faster queries
    __table_args__ = (
        Index('idx_alert_alert_level', 'alert_level'),
        Index('idx_alert_player_name', 'player_name'),
        Index('idx_alert_fixture_date', 'fixture_date'),
        Index('idx_alert_fixture', 'fixture'),
        Index('idx_alert_player_name_fixture', 'player_name', 'fixture'),
    )
    
    def __repr__(self):
        """String representation of Alert."""
        return f"<Alert(id={self.id}, player_name='{self.player_name}', fixture='{self.fixture}', alert_level={self.alert_level.value})>"
    
    def to_dict(self):
        """
        Convert alert to dictionary format.
        
        Returns:
            dict: Alert data as dictionary
        """
        return {
            'id': self.id,
            'player_name': self.player_name,
            'fixture': self.fixture,
            'fixture_date': self.fixture_date.isoformat() if self.fixture_date else None,
            'alert_level': self.alert_level.value,
            'description': self.description,
            'last_alert_update': self.last_alert_update.isoformat() if self.last_alert_update else None,
            'acknowledged': self.acknowledged,
            'active_projection': self.active_projection,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
