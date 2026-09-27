"""Event service — reads from the existing mission session/status system."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from backend.services.mission_service import get_mission_service


def get_recent_events(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Return recent mission events (no fake events)."""
    service = get_mission_service()
    if limit is None:
        return service.get_recent_events()
    return service.get_recent_events(limit)


def get_event_count() -> int:
    return get_mission_service().status_api.get_event_count()

