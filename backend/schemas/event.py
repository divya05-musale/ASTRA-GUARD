"""Event schemas (minimal)."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EventsResponse(BaseModel):
    events: List[Dict[str, Any]] = []
    count: int = 0


class PerceptionEventRequest(BaseModel):
    """Pydantic request schema for a live PerceptionEvent.

    Mirrors agent.perception.perception_event.PerceptionEvent without
    duplicating any decision logic. ``source`` defaults to "camera" and
    invalid sources are rejected by the PerceptionEvent dataclass itself
    (mapped to HTTP 422 in the route).
    """

    timestamp: Optional[str] = None
    objects: List[Dict[str, Any]] = Field(default_factory=list)
    hands: List[Dict[str, Any]] = Field(default_factory=list)
    source: str = "camera"


