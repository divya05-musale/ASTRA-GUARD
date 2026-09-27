"""HandDetector alias wrapping HandTracker for API compatibility.

The canonical implementation lives in :mod:`agent.perception.hand_tracker`.
This module re-exports :class:`HandTracker` as :class:`HandDetector` so older
imports such as ``from agent.perception.hand_detector import HandDetector``
continue to work without changes.
"""
from __future__ import annotations

from agent.perception.hand_tracker import HandTracker as HandDetector  # noqa: F401

__all__ = ["HandDetector"]
