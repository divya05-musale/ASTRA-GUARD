
"""
Bridge between ASTRA-GUARD perception and protocol observations.

Phase 7.5.4 Step 1:
Connects perception with the protocol-aware ActivityInterpreter.

Flow:

PerceptionEvent
    ↓
Protocol Object Mapping
    ↓
Protocol Object Validation
    ↓
Optional ActivityInterpreter
    ↓
ProtocolObservation

Backward compatibility:
- Without current_step_id:
    Existing generic perception behavior is preserved.
- With current_step_id:
    ActivityInterpreter produces the protocol activity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt
from typing import Any, Dict, List, Optional

from agent.mission.activity_interpreter import ActivityInterpreter
from agent.mission.protocol_object_validator import (
    ProtocolObjectValidator,
)
from agent.perception.object_mapping import map_detected_object
from agent.perception.perception_event import PerceptionEvent


HAND_OBJECT_DISTANCE_THRESHOLD = 150.0

MIN_OBJECT_CONFIDENCE = 0.40


@dataclass
class ProtocolObservation:
    """Protocol-compatible observation generated from perception."""

    timestamp: str = ""
    activity: str = "UNKNOWN"
    object: Optional[str] = None
    confidence: float = 0.0
    source: str = "camera"
    raw_object: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Return the observation as a dictionary."""

        return {
            "timestamp": self.timestamp,
            "activity": self.activity,
            "object": self.object,
            "confidence": self.confidence,
            "source": self.source,
            "raw_object": self.raw_object,
            "metadata": self.metadata,
        }


class PerceptionProtocolBridge:
    """Convert perception events into protocol observations."""

    def __init__(
        self,
        hand_object_distance_threshold: float = (
            HAND_OBJECT_DISTANCE_THRESHOLD
        ),
        min_object_confidence: float = MIN_OBJECT_CONFIDENCE,
        protocol_objects=None,
        activity_interpreter: ActivityInterpreter | None = None,
        expected_object_by_step: Dict[str, str] | None = None,
    ) -> None:

        self.hand_object_distance_threshold = float(
            hand_object_distance_threshold
        )

        self.min_object_confidence = float(
            min_object_confidence
        )

        self.object_validator = None

        if protocol_objects is not None:
            self.object_validator = ProtocolObjectValidator(
                protocol_objects
            )

        self.activity_interpreter = (
            activity_interpreter
            or ActivityInterpreter()
        )
        self.expected_object_by_step = dict(expected_object_by_step or {})

    @staticmethod
    def _clamp_confidence(value: float) -> float:
        """Keep confidence within the range 0.0 to 1.0."""

        return max(
            0.0,
            min(1.0, float(value)),
        )

    @staticmethod
    def _get_object_center(
        obj: Dict[str, Any],
    ) -> Optional[tuple]:
        """Return object center in pixel coordinates."""

        bbox = obj.get("bbox")

        if isinstance(bbox, dict):
            try:
                x1 = float(bbox["x1"])
                y1 = float(bbox["y1"])
                x2 = float(bbox["x2"])
                y2 = float(bbox["y2"])

                return (
                    (x1 + x2) / 2.0,
                    (y1 + y2) / 2.0,
                )

            except (
                KeyError,
                TypeError,
                ValueError,
            ):
                pass

        if (
            isinstance(bbox, (list, tuple))
            and len(bbox) >= 4
        ):
            try:
                x1, y1, x2, y2 = map(
                    float,
                    bbox[:4],
                )

                return (
                    (x1 + x2) / 2.0,
                    (y1 + y2) / 2.0,
                )

            except (
                TypeError,
                ValueError,
            ):
                pass

        try:
            if all(
                key in obj
                for key in (
                    "x1",
                    "y1",
                    "x2",
                    "y2",
                )
            ):
                x1 = float(obj["x1"])
                y1 = float(obj["y1"])
                x2 = float(obj["x2"])
                y2 = float(obj["y2"])

                return (
                    (x1 + x2) / 2.0,
                    (y1 + y2) / 2.0,
                )

        except (
            TypeError,
            ValueError,
        ):
            pass

        center = obj.get("center")

        if isinstance(center, dict):
            try:
                return (
                    float(center["x"]),
                    float(center["y"]),
                )

            except (
                KeyError,
                TypeError,
                ValueError,
            ):
                pass

        if (
            isinstance(center, (list, tuple))
            and len(center) >= 2
        ):
            try:
                return (
                    float(center[0]),
                    float(center[1]),
                )

            except (
                TypeError,
                ValueError,
            ):
                pass

        return None

    @staticmethod
    def _get_hand_center(
        hand: Dict[str, Any],
    ) -> Optional[tuple]:
        """Extract the center point from a hand detection."""

        center = hand.get("center")

        if (
            isinstance(center, (list, tuple))
            and len(center) >= 2
        ):
            try:
                return (
                    float(center[0]),
                    float(center[1]),
                )

            except (
                TypeError,
                ValueError,
            ):
                pass

        landmarks = hand.get("landmarks")

        if (
            isinstance(landmarks, list)
            and landmarks
        ):
            points = []

            for landmark in landmarks:

                if isinstance(landmark, dict):
                    x = landmark.get("x")
                    y = landmark.get("y")

                    if x is not None and y is not None:
                        try:
                            points.append(
                                (
                                    float(x),
                                    float(y),
                                )
                            )

                        except (
                            TypeError,
                            ValueError,
                        ):
                            continue

                elif (
                    isinstance(landmark, (list, tuple))
                    and len(landmark) >= 2
                ):
                    try:
                        points.append(
                            (
                                float(landmark[0]),
                                float(landmark[1]),
                            )
                        )

                    except (
                        TypeError,
                        ValueError,
                    ):
                        continue

            if points:
                return (
                    sum(
                        point[0]
                        for point in points
                    )
                    / len(points),
                    sum(
                        point[1]
                        for point in points
                    )
                    / len(points),
                )

        return None

    def _hand_near_object(
        self,
        obj: Dict[str, Any],
        hands: List[Dict[str, Any]],
    ) -> tuple:
        """Determine whether a hand is interacting with an object."""

        object_center = self._get_object_center(obj)

        if object_center is None:
            return (
                False,
                0.0,
                None,
            )

        best_distance = None
        best_hand_confidence = 0.0

        for hand in hands:

            hand_center = self._get_hand_center(hand)

            if hand_center is None:
                continue

            distance = sqrt(
                (
                    object_center[0]
                    - hand_center[0]
                ) ** 2
                + (
                    object_center[1]
                    - hand_center[1]
                ) ** 2
            )

            if (
                best_distance is None
                or distance < best_distance
            ):
                best_distance = distance

                try:
                    best_hand_confidence = float(
                        hand.get(
                            "confidence",
                            0.0,
                        )
                    )

                except (
                    TypeError,
                    ValueError,
                ):
                    best_hand_confidence = 0.0

        if best_distance is None:
            return (
                False,
                0.0,
                None,
            )

        return (
            best_distance
            <= self.hand_object_distance_threshold,
            self._clamp_confidence(
                best_hand_confidence
            ),
            best_distance,
        )

    def _select_object(
        self,
        objects: List[Dict[str, Any]],
        expected_object: str | None = None,
    ) -> Optional[Dict[str, Any]]:
        """Select the highest-confidence valid protocol object."""

        candidates = []

        for obj in objects:

            if not isinstance(
                obj,
                dict,
            ):
                continue

            raw_name = (
                obj.get("name")
                or obj.get("class_name")
                or obj.get("label")
                or obj.get("class")
            )

            if not isinstance(
                raw_name,
                str,
            ):
                continue

            protocol_object = map_detected_object(
                raw_name
            )

            if protocol_object is None:
                continue

            if (
                self.object_validator is not None
                and not self.object_validator.is_valid(
                    protocol_object
                )
            ):
                continue

            try:
                confidence = float(
                    obj.get(
                        "confidence",
                        0.0,
                    )
                )

            except (
                TypeError,
                ValueError,
            ):
                confidence = 0.0

            if (
                confidence
                < self.min_object_confidence
            ):
                continue

            candidates.append(
                (
                    confidence,
                    obj,
                    raw_name,
                    protocol_object,
                )
            )

        if not candidates:
            return None

        candidates.sort(
            key=lambda item: (
                item[3] == expected_object,
                item[0],
            ),
            reverse=True,
        )

        (
            confidence,
            obj,
            raw_name,
            protocol_object,
        ) = candidates[0]

        return {
            "object": obj,
            "raw_object": raw_name,
            "protocol_object": protocol_object,
            "confidence": confidence,
        }

    def convert(
        self,
        event: PerceptionEvent,
        current_step_id: str | None = None,
    ) -> ProtocolObservation:
        """
        Convert perception into a protocol observation.

        When current_step_id is provided, the ActivityInterpreter
        uses the current protocol step to determine the activity.

        When current_step_id is None, the original generic
        perception behavior is preserved.
        """

        if not isinstance(
            event,
            PerceptionEvent,
        ):
            raise TypeError(
                "event must be a PerceptionEvent"
            )

        expected_object = self.expected_object_by_step.get(current_step_id or "")
        selected = self._select_object(event.objects, expected_object)

        if selected is None:
            return ProtocolObservation(
                timestamp=event.timestamp,
                activity="UNKNOWN",
                object=None,
                confidence=0.0,
                source=event.source,
                raw_object=None,
                metadata={
                    "reason": (
                        "no_supported_object_detected"
                    ),
                    "step_id": current_step_id,
                },
            )

        selected_object = selected["object"]

        object_confidence = selected["confidence"]

        (
            is_near,
            hand_confidence,
            distance,
        ) = self._hand_near_object(
            selected_object,
            event.hands,
        )

        combined_confidence = (
            0.6 * object_confidence
            + 0.4 * hand_confidence
            if is_near
            else object_confidence * 0.80
        )

        combined_confidence = (
            self._clamp_confidence(
                combined_confidence
            )
        )

        # -------------------------------------------------
        # Protocol-aware activity interpretation
        # -------------------------------------------------

        if current_step_id is not None:

            interpreted = (
                self.activity_interpreter.interpret(
                    step_id=current_step_id,
                    detected_object=selected[
                        "protocol_object"
                    ],
                    hand_interaction=is_near,
                    confidence=combined_confidence,
                )
            )

            activity = interpreted.get(
                "activity",
                "UNKNOWN",
            )

            activity_confidence = (
                self._clamp_confidence(
                    interpreted.get(
                        "confidence",
                        0.0,
                    )
                )
            )

            activity_reason = interpreted.get(
                "reason",
                "protocol_activity_interpretation",
            )

        # -------------------------------------------------
        # Backward-compatible generic perception behavior
        # -------------------------------------------------

        else:

            if is_near:

                activity = "PICK_SAMPLE"

                activity_confidence = (
                    self._clamp_confidence(
                        0.6 * object_confidence
                        + 0.4 * hand_confidence
                    )
                )

                activity_reason = (
                    "object_hand_interaction"
                )

            else:

                activity = "OBJECT_PRESENT"

                activity_confidence = (
                    self._clamp_confidence(
                        object_confidence
                    )
                )

                activity_reason = (
                    "object_detected_without_hand_interaction"
                )

        return ProtocolObservation(
            timestamp=event.timestamp,
            activity=activity,
            object=selected[
                "protocol_object"
            ],
            confidence=activity_confidence,
            source=event.source,
            raw_object=selected[
                "raw_object"
            ],
            metadata={
                "step_id": current_step_id,
                "hand_interaction": is_near,
                "hand_confidence": hand_confidence,
                "object_confidence": object_confidence,
                "hand_object_distance": distance,
                "activity_reason": activity_reason,
                "object_metadata": dict(selected_object.get("metadata") or {}),
            },
        )


def perception_to_protocol(
    event: PerceptionEvent,
) -> ProtocolObservation:
    """
    Convenience function for converting perception to protocol data.

    Uses the original generic perception behavior.
    """

    bridge = PerceptionProtocolBridge()

    return bridge.convert(event)
