
"""Structured perception event for ASTRA-GUARD Phase 6."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class PerceptionEvent:
    """
    Combined YOLO objects + MediaPipe hands for one frame.

    This class represents perception only.
    It does not perform protocol inference.
    """

    timestamp: str = ""

    objects: List[Dict[str, Any]] = field(
        default_factory=list
    )

    hands: List[Dict[str, Any]] = field(
        default_factory=list
    )

    source: str = "camera"

    def __post_init__(self) -> None:

        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

        if self.source not in {"camera", "video"}:
            raise ValueError(
                "PerceptionEvent source must be 'camera' or 'video'"
            )

        if not isinstance(self.objects, list):
            raise ValueError(
                "objects must be a list"
            )

        if not isinstance(self.hands, list):
            raise ValueError(
                "hands must be a list"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the event to a JSON-friendly dictionary."""

        hands = [
            {
                key: value
                for key, value in hand.items()
                if not key.startswith("_")
            }
            for hand in self.hands
        ]

        return {
            "timestamp": self.timestamp,
            "objects": list(self.objects),
            "hands": hands,
            "source": self.source,
        }
