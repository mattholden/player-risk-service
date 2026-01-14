"""
Alert Service for managing player alerts.

Handles saving, querying, and managing alerts in the database.
Provides a clean interface between the application layer and 
the Alert model.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from database.database import session_scope
from database.models.alert import Alert
from database.enums import AlertLevel

if TYPE_CHECKING:
    from src.agents.models import PlayerAlert


class AlertService:
    """
    Service for managing player alerts in the database.
    
    Usage:
        service = AlertService()
        
        # Save alerts from the agent pipeline
        count = service.save_alerts(player_alerts)
        
        # Query alerts
        alerts = service.get_alerts_for_fixture("Arsenal vs Brentford")
        active = service.get_active_alerts()
    """

    def __init__(self, run_id: str):
        self.run_id = run_id
    
    def save_alerts(self, alerts: List["PlayerAlert"]) -> int:
        """
        Save a batch of alerts to the database.
        
        Args:
            alerts: List of PlayerAlert objects from the agent pipeline
            
        Returns:
            int: Number of alerts saved
        """
        if not alerts:
            return 0
        
        print(f"\n💾 Saving {len(alerts)} alerts to database...")
        
        with session_scope() as session:
            saved_count = 0
            for alert in alerts:
                db_alert = Alert(
                    player_name=alert.player_name,
                    fixture=alert.fixture,
                    fixture_date=alert.fixture_date,
                    alert_level=alert.alert_level,
                    description=alert.description,
                    last_alert_update=datetime.now(),
                    acknowledged=False,
                    active_projection=True,
                    created_at=datetime.now(),
                    run_id=self.run_id
                )
                session.add(db_alert)
                saved_count += 1
        
        print(f"✅ Saved {saved_count} player alerts to database")
        return saved_count
    
    def get_alerts_for_fixture(self, fixture: str) -> List[Alert]:
        """
        Get all alerts for a specific fixture.
        
        Args:
            fixture: Fixture string (e.g., "Arsenal vs Brentford")
            
        Returns:
            List of Alert objects
        """
        with session_scope() as session:
            alerts = session.query(Alert).filter(
                Alert.fixture == fixture,
                Alert.active_projection.is_(True)
            ).all()
            
            # Detach from session
            return [self._detach_alert(a) for a in alerts]
    
    def get_alerts_for_fixtures(self, fixtures: List[str]) -> List[Alert]:
        """
        Get all alerts for multiple fixtures.
        
        Args:
            fixtures: List of fixture strings
            
        Returns:
            List of Alert objects
        """
        if not fixtures:
            return []
        
        with session_scope() as session:
            alerts = session.query(Alert).filter(
                Alert.fixture.in_(fixtures),
                Alert.active_projection.is_(True)
            ).all()
            
            return [self._detach_alert(a) for a in alerts]
    
    def get_latest_alerts_for_fixtures(self, fixtures: List[str]) -> List[Alert]:
        """
        Get the most recent alert for each player/fixture combination.
        
        This is useful for enrichment pipelines that run multiple times
        and should only use the latest assessment for each player.
        
        Args:
            fixtures: List of fixture strings
            
        Returns:
            List of Alert objects (one per unique player/fixture)
        """
        if not fixtures:
            return []
        
        with session_scope() as session:
            from sqlalchemy import func
            
            # Subquery to get the max created_at for each player/fixture
            latest_subquery = session.query(
                Alert.player_name,
                Alert.fixture,
                func.max(Alert.created_at).label('max_created')
            ).filter(
                Alert.fixture.in_(fixtures),
                Alert.active_projection.is_(True)
            ).group_by(
                Alert.player_name,
                Alert.fixture
            ).subquery()
            
            # Join to get the full alert records
            alerts = session.query(Alert).join(
                latest_subquery,
                (Alert.player_name == latest_subquery.c.player_name) &
                (Alert.fixture == latest_subquery.c.fixture) &
                (Alert.created_at == latest_subquery.c.max_created)
            ).filter(
                Alert.active_projection.is_(True)
            ).all()
            
            return [self._detach_alert(a) for a in alerts]
    
    def get_active_alerts(self) -> List[Alert]:
        """
        Get all active alerts (where active_projection is True).
        
        Returns:
            List of Alert objects
        """
        with session_scope() as session:
            alerts = session.query(Alert).filter(
                Alert.active_projection.is_(True)
            ).order_by(Alert.fixture_date).all()
            
            return [self._detach_alert(a) for a in alerts]
    
    def get_alerts_since(self, since: datetime) -> List[Alert]:
        """
        Get alerts created since a specific date.
        
        Args:
            since: Datetime to filter from
            
        Returns:
            List of Alert objects created after the given date
        """
        with session_scope() as session:
            alerts = session.query(Alert).filter(
                Alert.created_at >= since
            ).order_by(Alert.created_at.desc()).all()
            
            return [self._detach_alert(a) for a in alerts]
    
    def get_alerts_by_level(
        self, 
        levels: List[AlertLevel],
        active_only: bool = True
    ) -> List[Alert]:
        """
        Get alerts filtered by alert level.
        
        Args:
            levels: List of AlertLevel values to include
            active_only: If True, only return active projections
            
        Returns:
            List of Alert objects matching the levels
        """
        with session_scope() as session:
            query = session.query(Alert).filter(
                Alert.alert_level.in_(levels)
            )
            
            if active_only:
                query = query.filter(Alert.active_projection.is_(True))
            
            alerts = query.order_by(Alert.fixture_date).all()
            
            return [self._detach_alert(a) for a in alerts]
    
    def deactivate_fixture_alerts(self, fixture: str) -> int:
        """
        Mark all alerts for a fixture as inactive.
        
        Useful after a match has been played.
        
        Args:
            fixture: Fixture string
            
        Returns:
            int: Number of alerts deactivated
        """
        with session_scope() as session:
            count = session.query(Alert).filter(
                Alert.fixture == fixture,
                Alert.active_projection.is_(True)
            ).update({Alert.active_projection: False})
            
            return count
    
    def _detach_alert(self, alert: Alert) -> Alert:
        """
        Create a detached copy of an alert to use outside the session.
        
        Args:
            alert: Alert object from session
            
        Returns:
            Detached Alert object
        """
        return Alert(
            id=alert.id,
            run_id=alert.run_id,
            player_name=alert.player_name,
            fixture=alert.fixture,
            fixture_date=alert.fixture_date,
            alert_level=alert.alert_level,
            description=alert.description,
            last_alert_update=alert.last_alert_update,
            acknowledged=alert.acknowledged,
            active_projection=alert.active_projection,
            created_at=alert.created_at
        )

    def get_alerts_by_run_id(self, run_id: str) -> List[Alert]:
        """Get all alerts from a specific pipeline run."""
        with session_scope() as session:
            alerts = session.query(Alert).filter(
                Alert.run_id == run_id
            ).order_by(Alert.created_at).all()
            
            return [self._detach_alert(a) for a in alerts]

