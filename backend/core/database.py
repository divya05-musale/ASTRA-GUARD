"""Lightweight in-memory store for dashboards. Intentionally SQL-free."""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Deque, Dict, List, Optional


@dataclass
class InMemoryStore:
    events: Deque[Dict[str, Any]] = field(default_factory=lambda: deque(maxlen=4096))
    decisions: Deque[Dict[str, Any]] = field(default_factory=lambda: deque(maxlen=1024))
    latest_progress: Dict[str, Any] = field(default_factory=dict)
    latest_perception: Dict[str, Any] = field(default_factory=dict)
    mission_status: Dict[str, Any] = field(default_factory=dict)
    camera_status: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def push_event(self, event: Dict[str, Any]) -> None:
        if "timestamp" not in event:
            event = {"timestamp": datetime.now().isoformat(), **event}
        self.events.append(event)

    def push_decision(self, decision: Dict[str, Any]) -> None:
        if "timestamp" not in decision:
            decision = {"timestamp": datetime.now().isoformat(), **decision}
        self.decisions.append(decision)

    def latest_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        n = max(1, int(limit))
        return list(reversed(list(self.events)[-n:]))

    def latest_decisions(self, limit: int = 25) -> List[Dict[str, Any]]:
        n = max(1, int(limit))
        return list(reversed(list(self.decisions)[-n:]))


_store: Optional[InMemoryStore] = None
_store_lock = threading.Lock()


def get_store() -> InMemoryStore:
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = InMemoryStore()
    return _store


def reset_store() -> None:
    global _store
    with _store_lock:
        _store = InMemoryStore()
