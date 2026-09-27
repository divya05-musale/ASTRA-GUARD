"""Events endpoint — reads real events from the mission session."""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from agent.perception.perception_event import PerceptionEvent
from backend.schemas.event import PerceptionEventRequest
from backend.services.event_service import get_recent_events
from backend.services.mission_service import get_mission_service

router = APIRouter()


@router.get("/events")
def list_events(
    limit: Optional[int] = Query(default=None, ge=0),
) -> List[Dict[str, Any]]:
    return get_recent_events(limit)


@router.post("/mission/event")
def post_mission_event(payload: PerceptionEventRequest) -> Dict[str, Any]:
    """Process one live perception event through the real mission engine.

    Reuses the singleton LivePerceptionSession.process_event() — no
    duplicated decision logic, no fake events.
    """
    try:
        event = PerceptionEvent(
            timestamp=payload.timestamp or "",
            objects=payload.objects,
            hands=payload.hands,
            source=payload.source,
        )
    except ValueError as exc:
        # e.g. PerceptionEvent rejects source != "camera".
        raise HTTPException(status_code=422, detail=str(exc))

    try:
        result = get_mission_service().process_event(event)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return result

