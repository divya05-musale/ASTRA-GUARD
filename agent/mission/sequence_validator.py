"""Sequence validator: compare detected event to expected step."""
from __future__ import annotations
from typing import Any, Dict, List


class SequenceValidator:
    """Deterministic validator. Never advances state."""

    def __init__(self, steps, activities=None, threshold: float = 0.70) -> None:
        ordered = sorted(list(steps), key=lambda s: s.get("order", 0))
        self._steps = ordered
        self._by_activity = {s.get("activity"): s for s in ordered}
        known = set(self._by_activity.keys())
        if activities:
            for a in activities:
                aid = a.get("activity_id") if isinstance(a, dict) else a
                if aid:
                    known.add(aid)
        self._known_activities = known
        self.threshold = float(threshold)

    def _expected(self, step_id: str) -> Dict[str, Any]:
        for s in self._steps:
            if s.get("step_id") == step_id:
                return s
        raise ValueError(f"Unknown step {step_id}")

    def validate(self, event: Dict[str, Any], step_id: str) -> Dict[str, Any]:
        exp = self._expected(step_id)
        act = event.get("activity")
        obj = event.get("object")
        metadata = event.get("metadata") or {}
        object_metadata = metadata.get("object_metadata") or {}

        if object_metadata.get("protocol_violation"):
            return {
                "activity_match": act == exp.get("activity"),
                "object_match": obj == exp.get("expected_object"),
                "confidence_ok": True,
                "valid": False,
                "reason": str(object_metadata["protocol_violation"]),
                "guidance": object_metadata.get("guidance"),
            }

        if object_metadata.get("uncertainty_reason"):
            return {
                "activity_match": act == exp.get("activity"),
                "object_match": obj == exp.get("expected_object"),
                "confidence_ok": False,
                "valid": False,
                "reason": "LOW_CONFIDENCE",
            }

        if (obj is None or metadata.get("reason") == "no_supported_object_detected") and exp.get("uncertain_on_no_detection"):
            return {
                "activity_match": act == exp.get("activity"),
                "object_match": False,
                "confidence_ok": False,
                "valid": False,
                "reason": "LOW_CONFIDENCE",
            }

        try:
            conf = float(event.get("confidence", 1.0))
        except (TypeError, ValueError):
            conf = 0.0
        if act not in self._known_activities:
            return {"activity_match": False, "object_match": False,
                    "confidence_ok": conf >= self.threshold,
                    "valid": False, "reason": "UNKNOWN_ACTION"}
        if conf < self.threshold:
            am = (act == exp.get("activity"))
            om = (obj == exp.get("expected_object"))
            return {"activity_match": am, "object_match": om,
                    "confidence_ok": False, "valid": False,
                    "reason": "LOW_CONFIDENCE"}
        if act != exp.get("activity"):
            return {"activity_match": False,
                    "object_match": (obj == exp.get("expected_object")),
                    "confidence_ok": True, "valid": False,
                    "reason": "WRONG_SEQUENCE"}
        if obj != exp.get("expected_object"):
            return {"activity_match": True, "object_match": False,
                    "confidence_ok": True, "valid": False,
                    "reason": "WRONG_OBJECT"}
        return {"activity_match": True, "object_match": True,
                "confidence_ok": True, "valid": True, "reason": None}

