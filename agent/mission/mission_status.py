"""
Phase 11 - Mission Status Service.

Provides dashboard-ready mission information
from the existing LivePerceptionSession.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agent.mission.live_perception_session import (
    LivePerceptionSession,
)


class MissionStatus:
    """Expose mission information for monitoring interfaces."""

    def __init__(
        self,
        session: LivePerceptionSession,
    ) -> None:
        if not isinstance(
            session,
            LivePerceptionSession,
        ):
            raise TypeError(
                "session must be a LivePerceptionSession"
            )

        self.session = session

    def _get_state_machine(self):
        """Return the protocol state machine."""

        return self.session.adapter.engine.sm

    def _get_total_steps(self) -> int:
        """Return the total number of protocol steps."""

        state_machine = self._get_state_machine()

        return len(state_machine._steps)

    def _get_completed_steps(self) -> int:
        """Return the number of completed protocol steps."""

        state_machine = self._get_state_machine()

        current_index = state_machine.step_index()

        if state_machine.is_complete():
            return self._get_total_steps()

        return current_index

    def get_progress(self) -> Dict[str, Any]:
        """
        Return current protocol progress.

        Progress is calculated from the protocol state machine.
        """

        state_machine = self._get_state_machine()

        total_steps = self._get_total_steps()

        completed_steps = self._get_completed_steps()

        current_index = state_machine.step_index()

        current_step_id = state_machine.current_step_id()

        if state_machine.is_complete():
            progress_percent = 100.0
        else:
            progress_percent = (
                completed_steps / total_steps
            ) * 100.0

        return {
            "current_step": current_step_id,
            "current_index": current_index,
            "completed_steps": completed_steps,
            "total_steps": total_steps,
            "progress_percent": round(
                progress_percent,
                1,
            ),
            "completed": state_machine.is_complete(),
        }

    def get_current_status(self) -> Dict[str, Any]:
        """Return the latest mission status."""

        result = self.session.get_last_result()

        progress = self.get_progress()

        if result is None:
            return {
                "active": False,
                "step_id": None,
                "activity": None,
                "expected_activity": None,
                "detected_object": None,
                "expected_object": None,
                "confidence": None,
                "status": "IDLE",
                "deviation": None,
                "guidance": None,
                "event_count": 0,
                "recent_events": [],
                "progress": progress,
            }

        perception = result.get("perception") or {}

        recent_events = [
            event.to_dict()
            for event in self.session.get_recent_events()
        ]

        return {
            "active": True,
            "step_id": result.get("step_id"),
            "activity": (
                result.get("detected_activity")
                or perception.get("activity")
            ),
            "expected_activity": result.get(
                "expected_activity"
            ),
            "detected_object": (
                result.get("detected_object")
                or perception.get("object")
            ),
            "expected_object": result.get(
                "expected_object"
            ),
            "confidence": perception.get(
                "confidence"
            ),
            "status": result.get(
                "status",
                "UNKNOWN",
            ),
            "deviation": result.get(
                "deviation_type"
            ),
            "guidance": result.get(
                "guidance"
            ),
            "event_count": self.session.event_count,
            "recent_events": recent_events,
            "progress": progress,
        }

    def get_event_count(self) -> int:
        """Return the number of processed mission events."""

        return self.session.event_count

    def get_recent_events(
        self,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Return recent mission events."""

        events = [
            event.to_dict()
            for event in self.session.get_recent_events()
        ]

        if limit is None:
            return events

        if not isinstance(limit, int):
            raise TypeError(
                "limit must be an integer"
            )

        if limit < 0:
            raise ValueError(
                "limit must be non-negative"
            )

        if limit == 0:
            return []

        return events[-limit:]

    def get_summary(self) -> Dict[str, Any]:
        """Return a compact mission summary."""

        event_store = self.session.event_store
        counts = event_store.get_counts()

        summary = {
            "total_events": event_store.count(),
            "correct": counts.get("CORRECT", 0),
            "deviations": counts.get("DEVIATION", 0),
            "uncertain": counts.get("UNCERTAIN", 0),
            "completed": counts.get("COMPLETED", 0),
        }
        return summary