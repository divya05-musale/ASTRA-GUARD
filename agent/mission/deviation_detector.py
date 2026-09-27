"""Deviation detector: categorize invalid events deterministically."""
from __future__ import annotations
from typing import Any, Dict, List


class DeviationDetector:
    """Classify deviations from already-interpreted events."""

    def __init__(self, steps, activities=None, threshold: float = 0.70) -> None:
        self._steps = sorted(list(steps), key=lambda s: s.get("order", 0))
        self._by_activity = {s.get("activity"): s for s in self._steps}
        self._by_id = {s.get("step_id"): s for s in self._steps}
        known = set(self._by_activity.keys())
        if activities:
            for a in activities:
                aid = a.get("activity_id") if isinstance(a, dict) else a
                if aid:
                    known.add(aid)
        self._known = known
        self.threshold = float(threshold)
        self._had_deviation = False

    def _expected(self, step_id: str) -> Dict[str, Any]:
        if step_id not in self._by_id:
            raise ValueError(f"Unknown step {step_id}")
        return self._by_id[step_id]

    def _order_of_activity(self, activity: str):
        step = self._by_activity.get(activity)
        return step.get("order") if step else None

    def detect(self, event: Dict[str, Any], step_id: str) -> Dict[str, Any]:
        exp = self._expected(step_id)
        act = event.get("activity")
        obj = event.get("object")
        try:
            conf = float(event.get("confidence", 1.0))
        except (TypeError, ValueError):
            conf = 0.0
        if act not in self._known:
            self._had_deviation = True
            return {"deviation_type": "UNKNOWN_ACTION", "recovered": False}
        if conf < self.threshold:
            self._had_deviation = True
            return {"deviation_type": "LOW_CONFIDENCE", "recovered": False}
        if act == exp.get("activity") and obj == exp.get("expected_object"):
            rec = self._had_deviation
            self._had_deviation = False
            if rec:
                return {"deviation_type": "RECOVERED", "recovered": True}
            return {"deviation_type": None, "recovered": False}
        if act == exp.get("activity") and obj != exp.get("expected_object"):
            self._had_deviation = True
            return {"deviation_type": "WRONG_OBJECT", "recovered": False}
        cur_order = exp.get("order")
        act_order = self._order_of_activity(act)
        if act_order is not None and act_order > cur_order:
            self._had_deviation = True
            if act in ("START_EXPERIMENT", "COMPLETE_EXPERIMENT", "RECORD_RESULT"):
                return {"deviation_type": "PREMATURE_ACTION", "recovered": False}
            if act_order > cur_order + 1:
                return {"deviation_type": "SKIPPED_STEP", "recovered": False}
            return {"deviation_type": "WRONG_SEQUENCE", "recovered": False}
        if act_order is not None and act_order < cur_order:
            self._had_deviation = True
            return {"deviation_type": "REPEATED_STEP", "recovered": False}
        self._had_deviation = True
        return {"deviation_type": "WRONG_SEQUENCE", "recovered": False}

    def check_timeout(self, elapsed_sec: float, step_id: str) -> Dict[str, Any]:
        exp = self._expected(step_id)
        timeout = float(exp.get("timeout_sec", 0))
        if elapsed_sec > timeout:
            return {"deviation_type": "TIMEOUT", "recovered": False}
        return {"deviation_type": None, "recovered": False}

