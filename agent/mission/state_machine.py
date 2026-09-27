"""Protocol state machine: tracks current step without skipping."""
from __future__ import annotations

from typing import Any, Dict, List


class ProtocolStateMachine:
    """Track position in an ordered step list."""

    def __init__(self, steps: List[Dict[str, Any]]) -> None:
        if not steps:
            raise ValueError("Protocol must contain steps")

        ordered = sorted(
            list(steps),
            key=lambda s: s.get("order", 0),
        )

        self._steps = ordered
        self._index = 0
        self._completed = False

    def current_step(self) -> Dict[str, Any]:
        """Return the current protocol step."""
        return self._steps[self._index]

    def current_step_id(self) -> str:
        """Return the current step ID."""
        return str(self._steps[self._index].get("step_id"))

    def step_index(self) -> int:
        """Return the zero-based current step index."""
        return self._index

    def next_step(self) -> Dict[str, Any] | None:
        """Return the next step without changing state."""
        if self._index + 1 < len(self._steps):
            return self._steps[self._index + 1]

        return None

    def advance(self) -> Dict[str, Any] | None:
        """Move one step forward. Never skips."""
        if self._completed:
            return None

        if self._index >= len(self._steps) - 1:
            self._completed = True
            return None

        self._index += 1
        return self._steps[self._index]

    def complete_current(self) -> None:
        """Mark the final step as completed."""
        if self._index >= len(self._steps) - 1:
            self._completed = True

    def reset(self) -> None:
        """Reset the protocol to the first step."""
        self._index = 0
        self._completed = False

    def is_complete(self) -> bool:
        """Return whether the protocol is complete."""
        return self._completed