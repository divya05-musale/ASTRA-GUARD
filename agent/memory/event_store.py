"""
Mission event history for ASTRA-GUARD.

The EventStore keeps a chronological record of protocol decisions
during the current mission session.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class MissionEvent:
    """A single event recorded during mission execution."""

    timestamp: str
    step_id: Optional[str]
    activity: Optional[str]
    detected_object: Optional[str]
    confidence: Optional[float]
    status: str
    deviation: Optional[str]
    guidance: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        """Return the event as a dictionary."""
        return asdict(self)


class EventStore:
    """Bounded in-memory event window with lifetime status counters."""

    def __init__(self, max_events: int = 4096) -> None:
        if not isinstance(max_events, int) or max_events < 1:
            raise ValueError("max_events must be a positive integer")
        self._events: deque[MissionEvent] = deque(maxlen=max_events)
        self._total_events = 0
        self._counts: Dict[str, int] = {}

    def record(
        self,
        *,
        step_id: Optional[str],
        activity: Optional[str],
        detected_object: Optional[str],
        confidence: Optional[float],
        status: str,
        deviation: Optional[str] = None,
        guidance: Optional[str] = None,
    ) -> MissionEvent:
        """
        Record a mission event and return the created event.
        """

        event = MissionEvent(
            timestamp=datetime.now().isoformat(timespec="seconds"),
            step_id=step_id,
            activity=activity,
            detected_object=detected_object,
            confidence=confidence,
            status=status,
            deviation=deviation,
            guidance=guidance,
        )

        self._events.append(event)
        self._total_events += 1
        self._counts[status] = self._counts.get(status, 0) + 1
        return event

    def get_all(self) -> List[MissionEvent]:
        """Return all recorded events in chronological order."""
        return list(self._events)

    def get_latest(self) -> Optional[MissionEvent]:
        """Return the most recent event, if available."""
        if not self._events:
            return None

        return self._events[-1]

    def count(self) -> int:
        """Return the number of recorded events."""
        return self._total_events

    def get_counts(self) -> Dict[str, int]:
        """Return lifetime decision counts by status."""
        return dict(self._counts)

    def clear(self) -> None:
        """Clear all events from the current mission session."""
        self._events.clear()
        self._total_events = 0
        self._counts.clear()