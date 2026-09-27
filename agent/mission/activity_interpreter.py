"""
ASTRA-GUARD activity interpreter.

Phase 7.5.2:
Converts perception observations into protocol activity IDs.

This is a deterministic prototype interpreter.
It does not use an LLM or train a new model.

Handles empty / unknown perception output explicitly so the downstream
decision engine receives a clear, categorizable event instead of a raw
`UNKNOWN_ACTION` / None tuple.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional


KNOWN_EMPTY_OBJECT_MARKERS = {"", None, "unknown", "none", "null", "n/a"}


def _clean_object(obj: Any) -> Optional[str]:
    if obj is None:
        return None
    if isinstance(obj, dict):
        obj = obj.get("object_id") or obj.get("class_name") or obj.get("id")
    if not isinstance(obj, str):
        try:
            obj = str(obj)
        except Exception:
            return None
    stripped = obj.strip()
    if stripped.lower() in KNOWN_EMPTY_OBJECT_MARKERS:
        return None
    return stripped


def _has_hand_interaction(hands: Any, threshold: int = 1) -> bool:
    if hands is None:
        return False
    if isinstance(hands, bool):
        return hands
    if isinstance(hands, (list, tuple, set)):
        return len(list(hands)) >= threshold
    if isinstance(hands, dict):
        return len(hands) >= threshold
    try:
        return bool(hands)
    except Exception:
        return False


class ActivityInterpreter:
    """Interpret perception signals using the current protocol step."""

    def __init__(self, activity_by_step: Dict[str, str] | None = None) -> None:
        self._activity_by_step = dict(activity_by_step or {
            "S001": "CHECK_EQUIPMENT",
            "S002": "RETRIEVE_SAMPLE",
            "S003": "OPEN_CONTAINER",
            "S004": "TRANSFER_SAMPLE",
            "S005": "START_EXPERIMENT",
            "S006": "RECORD_RESULT",
            "S007": "SECURE_SAMPLE",
            "S008": "COMPLETE_EXPERIMENT",
        })

    def interpret(
        self,
        step_id: str,
        detected_object: Optional[str],
        hand_interaction: bool = False,
        confidence: float = 0.0,
        hands: Optional[Iterable[Any]] = None,
        objects: Optional[Iterable[Any]] = None,
    ) -> Dict[str, Any]:
        """Convert the current step + perception signals into a protocol activity.

        Returns a dict with keys: activity (str), confidence (float), reason (str).
        ``activity`` is guaranteed to be a non-empty string: either one of the
        protocol activity IDs, ``UNKNOWN_STEP``, ``NO_OBJECT``, or
        ``NO_HAND_INTERACTION`` so callers never need to map None.
        """
        activity = self._activity_by_step.get(step_id)
        if activity is None:
            return {
                "activity": "UNKNOWN_STEP",
                "confidence": 0.0,
                "reason": "unknown_step",
                "detected_object": None,
                "hand_interaction": False,
            }

        try:
            confidence = max(0.0, min(1.0, float(confidence)))
        except (TypeError, ValueError):
            confidence = 0.0

        if hands is not None:
            hand_interaction = hand_interaction or _has_hand_interaction(hands)

        cleaned_obj = _clean_object(detected_object)
        if cleaned_obj is None and objects:
            try:
                first = next(iter(objects))
                cleaned_obj = _clean_object(first)
            except StopIteration:
                cleaned_obj = None

        if cleaned_obj is None:
            return {
                "activity": "NO_OBJECT",
                "confidence": 0.0,
                "reason": "no_object_detected",
                "detected_object": None,
                "hand_interaction": hand_interaction,
            }

        if hand_interaction:
            activity_confidence = confidence
            reason = "object_hand_interaction"
        else:
            activity_confidence = confidence * 0.80
            reason = "object_detected_without_hand_interaction"

        return {
            "activity": activity,
            "confidence": activity_confidence,
            "reason": reason,
            "detected_object": cleaned_obj,
            "hand_interaction": hand_interaction,
        }
