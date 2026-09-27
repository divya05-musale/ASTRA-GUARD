"""
Short-term memory for ASTRA-GUARD.

ShortTermMemory keeps a small rolling window of recent mission
events for immediate contextual awareness.
"""

from __future__ import annotations

from collections import deque
from typing import List

from agent.memory.event_store import MissionEvent


class ShortTermMemory:
    """Keep a rolling window of the most recent mission events."""

    def __init__(self, capacity: int = 30) -> None:
        if not isinstance(capacity, int):
            raise TypeError(
                "capacity must be an integer"
            )

        if capacity <= 0:
            raise ValueError(
                "capacity must be greater than zero"
            )

        self.capacity = capacity
        self._events: deque[MissionEvent] = deque(
            maxlen=capacity
        )

    def add(self, event: MissionEvent) -> None:
        """Add a mission event to short-term memory."""

        if not isinstance(event, MissionEvent):
            raise TypeError(
                "event must be a MissionEvent"
            )

        self._events.append(event)

    def get_recent(self) -> List[MissionEvent]:
        """Return recent events from oldest to newest."""

        return list(self._events)

    def get_latest(self) -> MissionEvent | None:
        """Return the most recent event."""

        if not self._events:
            return None

        return self._events[-1]

    def count(self) -> int:
        """Return the number of events currently stored."""

        return len(self._events)

    def clear(self) -> None:
        """Clear short-term memory."""

        self._events.clear()