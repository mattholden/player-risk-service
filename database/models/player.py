from database.base import Base
from sqlalchemy import Column, Integer, String, DateTime, Index
from datetime import datetime

class Player(Base):
    """
    Player model for tracking players.
    """
    __tablename__ = 'players'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Player information
    player_name = Column(String(200), nullable=False)
    team = Column(String(200), nullable=False)
    position = Column(String(10), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Indexes for faster queries
    __table_args__ = (
        Index('idx_player_player_name', 'player_name'),
        Index('idx_player_team', 'team'),
        Index('idx_player_position', 'position'),
    )

    def __repr__(self):
        """String representation of Player."""
        return f"<Player(id={self.id}, player_name='{self.player_name}', team='{self.team}', position='{self.position}')>"

    def to_dict(self):
        """Convert player to dictionary format."""
        return {
            'id': self.id,
            'player_name': self.player_name,
            'team': self.team,
            'position': self.position,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }