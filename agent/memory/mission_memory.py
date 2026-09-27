"""
Mission-level memory for ASTRA-GUARD.

MissionMemory provides a simple interface for reviewing
events recorded during the current mission session.
"""

from __future__ import annotations

from typing import Any, Dict, List

from agent.memory.event_store import EventStore, MissionEvent


class MissionMemory:
    """Provide mission-level access to recorded events."""

    def __init__(
        self,
        event_store: EventStore,
    ) -> None:
        if not isinstance(event_store, EventStore):
            raise TypeError(
                "event_store must be an EventStore"
            )

        self.event_store = event_store

    def get_history(self) -> List[MissionEvent]:
        """Return all mission events in chronological order."""

        return self.event_store.get_all()

    def get_recent(
        self,
        limit: int = 5,
    ) -> List[MissionEvent]:
        """Return the most recent mission events."""

        if not isinstance(limit, int):
            raise TypeError(
                "limit must be an integer"
            )

        if limit < 0:
            raise ValueError(
                "limit must be non-negative"
            )

        return self.event_store.get_all()[-limit:]

    def count_by_status(self) -> Dict[str, int]:
        """Return the number of events grouped by decision status."""

        counts: Dict[str, int] = {
            "CORRECT": 0,
            "DEVIATION": 0,
            "UNCERTAIN": 0,
            "COMPLETED": 0,
            "UNKNOWN": 0,
        }

        for status, count in self.event_store.get_counts().items():
            if status not in counts:
                counts[status] = 0
            counts[status] += count

        return counts

    def total_events(self) -> int:
        """Return the total number of recorded mission events."""

        return self.event_store.count()

    def get_summary(self) -> Dict[str, Any]:
        """Return a compact mission memory summary."""

        counts = self.count_by_status()

        return {
            "total_events": self.total_events(),
            "correct": counts["CORRECT"],
            "deviations": counts["DEVIATION"],
            "uncertain": counts["UNCERTAIN"],
            "completed": counts["COMPLETED"],
        }

    def clear(self) -> None:
        """Clear all events from mission memory."""

        self.event_store.clear()