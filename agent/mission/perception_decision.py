
"""
Phase 7.5.4 Step 2:
Protocol-aware perception-to-decision integration.

Connects the perception layer to the existing DecisionEngine.

Protocol-aware activity interpretation can be enabled explicitly
without breaking the existing generic perception behavior.
"""

from __future__ import annotations

from typing import Any, Dict

from agent.mission.perception_bridge import (
    PerceptionProtocolBridge,
    ProtocolObservation,
)
from agent.mission.decision_engine import DecisionEngine
from agent.perception.perception_event import PerceptionEvent


class PerceptionDecisionAdapter:
    """Convert perception events and send them to DecisionEngine."""

    def __init__(
        self,
        decision_engine: DecisionEngine,
        bridge: PerceptionProtocolBridge | None = None,
        protocol_aware: bool = False,
    ) -> None:
        if not isinstance(
            decision_engine,
            DecisionEngine,
        ):
            raise TypeError(
                "decision_engine must be a DecisionEngine"
            )

        self.engine = decision_engine

        self.bridge = (
            bridge
            or PerceptionProtocolBridge()
        )

        self.protocol_aware = bool(
            protocol_aware
        )

    def _get_current_step_id(self) -> str:
        """Return the current protocol step ID."""

        return self.engine.sm.current_step_id()

    def observe(
        self,
        event: PerceptionEvent,
    ) -> ProtocolObservation:
        """Convert perception into a protocol observation."""

        if not isinstance(
            event,
            PerceptionEvent,
        ):
            raise TypeError(
                "event must be a PerceptionEvent"
            )

        if self.protocol_aware:

            current_step_id = (
                self._get_current_step_id()
            )

            return self.bridge.convert(
                event,
                current_step_id=current_step_id,
            )

        # Preserve existing generic perception behavior.
        return self.bridge.convert(event)

    def decide(
        self,
        event: PerceptionEvent,
    ) -> Dict[str, Any]:
        """Convert perception and send it to DecisionEngine."""

        observation = self.observe(event)

        decision_event = {
            "timestamp": observation.timestamp,
            "activity": observation.activity,
            "object": observation.object,
            "confidence": observation.confidence,
            "source": observation.source,
            "metadata": observation.metadata,
        }

        decision = self.engine.process(
            decision_event
        )

        result = dict(decision)

        result["perception"] = (
            observation.to_dict()
        )

        return result

