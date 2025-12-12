"""
Services package - Business logic layer.

Contains service classes that implement:
- Article collection and storage
- Risk analysis orchestration
- Player tracking
- Alert generation
- Roster synchronization
"""

from src.services.roster_sync import RosterSyncService, PlayerData, SyncResult

__all__ = [
    'RosterSyncService',
    'PlayerData',
    'SyncResult',
]
