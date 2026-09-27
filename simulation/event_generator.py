"""Deterministic synthetic event generator (Phase 4)."""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

BASE_TIME = datetime(2026, 1, 1, 10, 0, 0)
VALID_ORIENTATIONS = (0, 90, 180, 270)
CONF_NORMAL = 0.95
CONF_MEDIUM = 0.85
CONF_LOW = 0.50


class EventGenerator:
    """Build synthetic detected events with deterministic metadata."""

    def __init__(self, base_time: datetime = BASE_TIME) -> None:
        self.base_time = base_time
        self._counter = 0

    def _timestamp(self, timestamp: Optional[str] = None) -> str:
        if timestamp:
            return timestamp
        ts = self.base_time + timedelta(seconds=self._counter)
        return ts.isoformat()

    def generate_event(self, activity: str, object: str, confidence: float = 0.95,
                       orientation: int = 0, timestamp: Optional[str] = None,
                       scenario: Optional[str] = None, tracking_id: Optional[str] = None,
                       notes: str = "", **extra: Any) -> Dict[str, Any]:
        if orientation not in VALID_ORIENTATIONS:
            raise ValueError(f"Invalid orientation {orientation}")
        conf = float(confidence)
        if not 0.0 <= conf <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        event: Dict[str, Any] = {"activity": activity, "object": object,
                                 "confidence": conf, "orientation": orientation,
                                 "timestamp": self._timestamp(timestamp),
                                 "source": "synthetic"}
        if scenario is not None:
            event["scenario"] = scenario
        if tracking_id is not None:
            event["tracking_id"] = tracking_id
        if notes:
            event["notes"] = notes
        event.update(extra)
        self._counter += 1
        return event

    def reset(self) -> None:
        self._counter = 0

