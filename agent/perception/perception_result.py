"""Perception result container for one processed frame.

Combines detections, hands, annotated BGR frame, and metadata into a single
object returned by LiveProcessor / WebcamRuntime consumers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import numpy as np


@dataclass
class PerceptionResult:
    """Structured result after running perception on one frame."""

    frame_bgr: Optional[np.ndarray] = None
    annotated_bgr: Optional[np.ndarray] = None
    objects: List[Dict[str, Any]] = field(default_factory=list)
    hands: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    decision: Optional[Dict[str, Any]] = None
    progress: Optional[Dict[str, Any]] = None
    frame_id: int = 0
    timestamp: str = ""
    source: str = "camera"
    processing_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-safe dict representation (no numpy arrays)."""
        out: Dict[str, Any] = {
            "frame_id": self.frame_id,
            "timestamp": self.timestamp,
            "source": self.source,
            "objects": list(self.objects),
            "hands": [
                {k: v for k, v in h.items() if not k.startswith("_")}
                for h in self.hands
            ],
            "events": list(self.events),
            "processing_ms": float(self.processing_ms),
        }
        if self.decision is not None:
            out["decision"] = dict(self.decision)
        if self.progress is not None:
            out["progress"] = dict(self.progress)
        out["has_frame"] = self.frame_bgr is not None
        out["has_annotated"] = self.annotated_bgr is not None
        return out
