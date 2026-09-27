"""Simple Pydantic schemas (kept minimal on purpose)."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str


class ProgressResponse(BaseModel):
    current_step: Optional[str] = None
    current_index: int = 0
    completed_steps: int = 0
    total_steps: int = 0
    progress_percent: float = 0.0
    completed: bool = False


class SummaryResponse(BaseModel):
    total_events: int = 0
    correct: int = 0
    deviations: int = 0
    uncertain: int = 0
    completed: int = 0


class MissionOverview(BaseModel):
    protocol_id: Optional[str] = None
    protocol_name: Optional[str] = None
    environment: Optional[str] = None
    protocol_type: Optional[str] = None
    current_step: Optional[str] = None
    progress: Dict[str, Any] = {}
    status: Optional[str] = None


class EventsResponse(BaseModel):
    events: List[Dict[str, Any]] = []
    count: int = 0

