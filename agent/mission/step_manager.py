"""Step manager: read-only access to current/expected step data."""
from __future__ import annotations
from typing import Any, Dict, List, Optional


class StepManager:
    """Expose expected activity/object/timeout/guidance for current step."""

    def __init__(self, steps: List[Dict[str, Any]], state_machine=None, rules=None) -> None:
        if not steps:
            raise ValueError("Protocol must contain steps")
        self._steps = sorted(list(steps), key=lambda s: s.get("order", 0))
        self._by_id = {s.get("step_id"): s for s in self._steps}
        self._by_order = {s.get("order"): s for s in self._steps}
        self._sm = state_machine
        self._rules = list(rules) if rules else []

    def _current(self) -> Dict[str, Any]:
        if self._sm is not None:
            return self._sm.current_step()
        return self._steps[0]

    def get_current_step(self) -> Dict[str, Any]:
        return self._current()

    def get_expected_activity(self) -> str:
        return str(self._current().get("activity"))

    def get_expected_object(self) -> str:
        return str(self._current().get("expected_object"))

    def get_timeout(self) -> int:
        return int(self._current().get("timeout_sec", 0))

    def get_description(self) -> str:
        return str(self._current().get("description", ""))

    def get_guidance(self) -> str:
        step_id = self._current().get("step_id")
        for rule in self._rules:
            if rule.get("step_id") == step_id and rule.get("result") == "ADVANCE":
                return str(rule.get("guidance", ""))
        return str(self._current().get("description", ""))

    def get_step(self, step_id: str) -> Optional[Dict[str, Any]]:
        return self._by_id.get(step_id)

    def get_step_by_order(self, order: int) -> Optional[Dict[str, Any]]:
        return self._by_order.get(order)

