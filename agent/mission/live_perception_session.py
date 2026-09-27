"""
Phase 7.4 live perception session.

Connects the live perception pipeline to the Phase 7.3
perception-to-decision adapter.

The session records mission decisions using EventStore
and keeps a rolling window using ShortTermMemory.

Voice guidance uses the same guidance text that is
shown on the ASTRA-GUARD dashboard.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agent.memory.event_store import EventStore, MissionEvent
from agent.memory.short_term_memory import ShortTermMemory
from agent.mission.perception_decision import PerceptionDecisionAdapter
from agent.perception.perception_event import PerceptionEvent
from agent.voice.voice_service import get_voice_guidance


class LivePerceptionSession:
    """Process live perception events through the mission engine."""

    def __init__(
        self,
        adapter: PerceptionDecisionAdapter,
        event_store: EventStore | None = None,
        short_term_memory: ShortTermMemory | None = None,
    ) -> None:
        if not isinstance(adapter, PerceptionDecisionAdapter):
            raise TypeError(
                "adapter must be a PerceptionDecisionAdapter"
            )

        if event_store is not None and not isinstance(
            event_store,
            EventStore,
        ):
            raise TypeError(
                "event_store must be an EventStore"
            )

        if short_term_memory is not None and not isinstance(
            short_term_memory,
            ShortTermMemory,
        ):
            raise TypeError(
                "short_term_memory must be a ShortTermMemory"
            )

        self.adapter = adapter

        self.event_store = event_store or EventStore()

        self.short_term_memory = (
            short_term_memory or ShortTermMemory()
        )

        self.event_count = 0
        self.last_result: Optional[Dict[str, Any]] = None

        # Offline local voice guidance service.
        self.voice_guidance = get_voice_guidance()

    def process_event(
        self,
        event: PerceptionEvent,
    ) -> Dict[str, Any]:
        """Process one live perception event and record its decision."""

        if not isinstance(event, PerceptionEvent):
            raise TypeError(
                "event must be a PerceptionEvent"
            )

        self.event_count += 1

        # Send perception through the existing protocol/decision engine.
        result = self.adapter.decide(event)

        self.last_result = result

        # Speak the same guidance that is shown on the dashboard.
        #
        # Important:
        # The voice assistant does NOT make mission decisions.
        # The existing protocol engine remains the source of truth.
        guidance = result.get("guidance")
        status = result.get("status")

        if guidance:
            self.voice_guidance.speak_decision(
                status=status,
                guidance=guidance,
                step_id=result.get("step_id"),
                deviation_type=result.get("deviation_type"),
                detected_object=result.get("detected_object"),
                expected_object=result.get("expected_object"),
                next_step_id=result.get("next_step_id"),
            )

        # Record the decision in mission memory.
        mission_event = self._record_decision(result)

        self.short_term_memory.add(mission_event)

        return result

    def _record_decision(
        self,
        result: Dict[str, Any],
    ) -> MissionEvent:
        """Record a decision result in the mission event store."""

        perception = result.get("perception") or {}

        return self.event_store.record(
            step_id=result.get("step_id"),
            activity=(
                result.get("detected_activity")
                or perception.get("activity")
            ),
            detected_object=(
                result.get("detected_object")
                or perception.get("object")
            ),
            confidence=perception.get("confidence"),
            status=str(
                result.get("status", "UNKNOWN")
            ),
            deviation=result.get("deviation_type"),
            guidance=result.get("guidance"),
        )

    def get_last_result(self) -> Optional[Dict[str, Any]]:
        """Return the most recent decision."""

        return self.last_result

    def get_event_history(self) -> List[MissionEvent]:
        """Return all recorded mission events."""

        return self.event_store.get_all()

    def get_latest_event(self) -> Optional[MissionEvent]:
        """Return the most recently recorded mission event."""

        return self.event_store.get_latest()

    def get_recent_events(self) -> List[MissionEvent]:
        """Return events currently held in short-term memory."""

        return self.short_term_memory.get_recent()

    def get_latest_recent_event(
        self,
    ) -> Optional[MissionEvent]:
        """Return the latest event from short-term memory."""

        return self.short_term_memory.get_latest()

    def reset(self) -> None:
        """Reset session state and both memory layers.

        Also resets the underlying protocol state machine so a new
        mission starts from the protocol's initial step instead of
        a stale COMPLETED state.

        The voice service is also reset so the same guidance can
        be spoken again in a new mission.
        """

        state_machine = getattr(
            getattr(
                getattr(self.adapter, "engine", None),
                "sm",
                None,
            ),
            "reset",
            None,
        )

        if callable(state_machine):
            state_machine()

        self.event_count = 0
        self.last_result = None

        self.event_store.clear()
        self.short_term_memory.clear()

        # Allow guidance to be spoken again after mission reset.
        self.voice_guidance.reset()