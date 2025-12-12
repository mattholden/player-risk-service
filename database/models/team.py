"""
Team database model for the team registry.

This model stores team metadata used for roster scraping, including
Transfermarkt identifiers and league associations. This is the source
of truth for which teams we track and how to find their data.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Index, UniqueConstraint
from database.base import Base


class Team(Base):
    """
    Team model for the team registry.
    
    Attributes:
        id: Primary key
        team_name: Canonical team name used throughout the system
        league: League name (e.g., "Premier League", "La Liga")
        country: Country code or name (e.g., "England", "Spain")
        transfermarkt_id: Team ID on Transfermarkt (for scraping)
        transfermarkt_slug: URL slug on Transfermarkt (e.g., "fc-arsenal")
        is_active: Whether we're actively tracking this team
        created_at: When this record was created
        updated_at: When this record was last updated
    """
    
    __tablename__ = 'teams'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Team identification
    team_name = Column(String(200), nullable=False)
    league = Column(String(100), nullable=False)
    country = Column(String(100), nullable=True)
    
    # Transfermarkt identifiers for scraping
    transfermarkt_id = Column(Integer, nullable=True, unique=True)
    transfermarkt_slug = Column(String(200), nullable=True)
    
    # Tracking status
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Indexes and constraints
    __table_args__ = (
        # Team name + league should be unique
        UniqueConstraint('team_name', 'league', name='uq_team_name_league'),
        
        # Indexes for common queries
        Index('idx_team_name', 'team_name'),
        Index('idx_team_league', 'league'),
        Index('idx_team_country', 'country'),
        Index('idx_team_is_active', 'is_active'),
        Index('idx_team_transfermarkt_id', 'transfermarkt_id'),
    )
    
    def __repr__(self):
        """String representation of Team."""
        status = "active" if self.is_active else "inactive"
        return f"<Team(id={self.id}, name='{self.team_name}', league='{self.league}', {status})>"
    
    def to_dict(self):
        """
        Convert team to dictionary format.
        
        Returns:
            dict: Team data as dictionary
        """
        return {
            'id': self.id,
            'team_name': self.team_name,
            'league': self.league,
            'country': self.country,
            'transfermarkt_id': self.transfermarkt_id,
            'transfermarkt_slug': self.transfermarkt_slug,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def get_transfermarkt_url(self) -> str | None:
        """
        Build the Transfermarkt squad URL for this team.
        
        Returns:
            str: Full URL to the team's squad page, or None if missing data
        """
        if not self.transfermarkt_id or not self.transfermarkt_slug:
            return None
        return f"https://www.transfermarkt.com/{self.transfermarkt_slug}/kader/verein/{self.transfermarkt_id}"

