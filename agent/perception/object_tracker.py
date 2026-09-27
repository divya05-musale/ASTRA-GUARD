"""Simple lightweight object tracker based on centroid distance matching.

Associates new detections with existing tracklets using IoU + centroid
distance. Used to provide stable ``track_id`` values across frames so that
downstream protocol code can reason about persistence of objects.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import time
import math


@dataclass
class Tracklet:
    track_id: int
    class_id: int
    class_name: str
    centroid: Dict[str, float]
    bbox: Dict[str, float]
    last_seen: float = field(default_factory=time.monotonic)
    hits: int = 0
    missed: int = 0


def _iou(a: Dict[str, float], b: Dict[str, float]) -> float:
    x1 = max(a["x1"], b["x1"])
    y1 = max(a["y1"], b["y1"])
    x2 = min(a["x2"], b["x2"])
    y2 = min(a["y2"], b["y2"])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if inter <= 0:
        return 0.0
    area_a = (a["x2"] - a["x1"]) * (a["y2"] - a["y1"])
    area_b = (b["x2"] - b["x1"]) * (b["y2"] - b["y1"])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _centroid_dist(a: Dict[str, float], b: Dict[str, float]) -> float:
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"])


class ObjectTracker:
    """Greedy association tracker. Single-thread use only."""

    def __init__(
        self,
        max_missed: int = 10,
        max_distance: float = 120.0,
        min_iou: float = 0.20,
    ) -> None:
        self.max_missed = int(max_missed)
        self.max_distance = float(max_distance)
        self.min_iou = float(min_iou)
        self._tracks: List[Tracklet] = []
        self._next_id: int = 1

    def reset(self) -> None:
        self._tracks.clear()
        self._next_id = 1

    def _centroid_of(self, bbox: Dict[str, float]) -> Dict[str, float]:
        return {
            "x": (float(bbox["x1"]) + float(bbox["x2"])) / 2.0,
            "y": (float(bbox["y1"]) + float(bbox["y2"])) / 2.0,
        }

    def update(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Associate detections with existing tracks and return enriched list.

        Each detection dict is augmented with ``track_id`` and ``age_hits``.
        """
        now = time.monotonic()
        output: List[Dict[str, Any]] = []
        used_tracks: set[int] = set()

        for det in detections:
            bbox = det.get("bbox")
            if not bbox:
                output.append({**det, "track_id": None})
                continue
            centroid = det.get("center") or self._centroid_of(bbox)
            best_track: Optional[Tracklet] = None
            best_score: float = -1.0
            best_idx: int = -1
            for idx, trk in enumerate(self._tracks):
                if idx in used_tracks:
                    continue
                if trk.class_id != int(det.get("class_id", -1)):
                    continue
                iou = _iou(trk.bbox, bbox)
                cd = _centroid_dist(trk.centroid, centroid)
                if iou < self.min_iou and cd > self.max_distance:
                    continue
                score = iou * 0.6 + max(0.0, 1.0 - cd / self.max_distance) * 0.4
                if score > best_score:
                    best_score = score
                    best_track = trk
                    best_idx = idx
            if best_track is not None:
                best_track.bbox = dict(bbox)
                best_track.centroid = centroid
                best_track.last_seen = now
                best_track.hits += 1
                best_track.missed = 0
                used_tracks.add(best_idx)
                output.append({**det, "track_id": best_track.track_id,
                               "age_hits": best_track.hits})
            else:
                new_trk = Tracklet(
                    track_id=self._next_id,
                    class_id=int(det.get("class_id", 0)),
                    class_name=str(det.get("class_name", "")),
                    centroid=centroid,
                    bbox=dict(bbox),
                    last_seen=now,
                    hits=1,
                    missed=0,
                )
                self._next_id += 1
                self._tracks.append(new_trk)
                output.append({**det, "track_id": new_trk.track_id, "age_hits": 1})

        surviving: List[Tracklet] = []
        for idx, trk in enumerate(self._tracks):
            if idx in used_tracks:
                surviving.append(trk)
                continue
            trk.missed += 1
            if trk.missed <= self.max_missed:
                surviving.append(trk)
        self._tracks = surviving
        return output

    def tracks(self) -> List[Dict[str, Any]]:
        """Snapshot of active tracklets."""
        return [
            {
                "track_id": t.track_id,
                "class_id": t.class_id,
                "class_name": t.class_name,
                "centroid": t.centroid,
                "bbox": t.bbox,
                "hits": t.hits,
                "missed": t.missed,
                "last_seen": t.last_seen,
            }
            for t in self._tracks
        ]
