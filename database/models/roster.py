"""
Roster database model for tracking active team rosters.

This model tracks which players are currently on which teams. A player can appear
on multiple rosters (e.g., club team and national team).

Key features:
- Tracks historical roster changes with start_date and end_date
- is_active flag for quick filtering of current rosters
- Composite unique constraint on (player_name, team, league, start_date)
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Index, UniqueConstraint
from database.base import Base


class Roster(Base):
    """
    Roster model for tracking player-team associations.
    
    Attributes:
        id: Primary key
        player_name: Name of the player
        team: Team name
        league: League name (e.g., "Premier League", "La Liga")
        position: Player position (e.g., "FW", "MF", "DF", "GK")
        is_active: Whether this roster entry is currently active
        start_date: When the player joined this team (or when we first detected them)
        end_date: When the player left this team (None if still active)
        created_at: When this record was created in our database
        updated_at: When this record was last updated
    """
    
    __tablename__ = 'rosters'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Player and team information
    player_name = Column(String(200), nullable=False)
    team = Column(String(200), nullable=False)
    league = Column(String(100), nullable=False)
    position = Column(String(10), nullable=True)
    
    # Active status and date tracking
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    start_date = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    end_date = Column(DateTime, nullable=True)
    
    # Tracking timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Indexes and constraints
    __table_args__ = (
        # Composite unique constraint: same player can be on same team multiple times
        # but only one active stint at a time (enforced via start_date)
        UniqueConstraint('player_name', 'team', 'league', 'start_date', 
                        name='uq_player_team_league_start'),
        
        # Indexes for common query patterns
        Index('idx_roster_player_name', 'player_name'),
        Index('idx_roster_team', 'team'),
        Index('idx_roster_league', 'league'),
        Index('idx_roster_is_active', 'is_active'),
        Index('idx_roster_team_league_active', 'team', 'league', 'is_active'),
        Index('idx_roster_start_date', 'start_date'),
        Index('idx_roster_end_date', 'end_date'),
    )
    
    def __repr__(self):
        """String representation of Roster."""
        status = "active" if self.is_active else "inactive"
        return (f"<Roster(id={self.id}, player='{self.player_name}', "
                f"team='{self.team}', league='{self.league}', {status})>")
    
    def to_dict(self):
        """
        Convert roster entry to dictionary format.
        
        Returns:
            dict: Roster data as dictionary
        """
        return {
            'id': self.id,
            'player_name': self.player_name,
            'team': self.team,
            'league': self.league,
            'position': self.position,
            'is_active': self.is_active,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def deactivate(self, end_date=None):
        """
        Mark this roster entry as inactive.
        
        Args:
            end_date: When the player left (defaults to now)
        """
        self.is_active = False
        self.end_date = end_date or datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)