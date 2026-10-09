"""
Phase 7.4 single-frame live perception processor.

Connects the existing Phase 6 YOLO + MediaPipe perception
components to the Phase 7.4 live mission session.

This module processes one frame at a time.
It does not open or control the webcam.
"""

from __future__ import annotations

from datetime import datetime
import time
from typing import Any, Dict, Optional

import numpy as np

from agent.mission.live_perception_session import LivePerceptionSession
from agent.perception.perception_event import PerceptionEvent


class LivePerceptionProcessor:
    """Convert one camera frame into a mission decision."""

    def __init__(
        self,
        object_detector: Any,
        hand_tracker: Any,
        session: LivePerceptionSession,
        backend_client: Optional[Any] = None,
    ) -> None:
        if not hasattr(object_detector, "detect"):
            raise TypeError(
                "object_detector must provide a detect(frame) method"
            )

        if hand_tracker is not None and not hasattr(hand_tracker, "process"):
            raise TypeError(
                "hand_tracker must provide a process(frame) method"
            )

        if not hasattr(session, "process_event"):
            raise TypeError(
                "session must provide a process_event(event) method"
            )

        if backend_client is not None and not hasattr(
            backend_client, "post_event"
        ):
            raise TypeError(
                "backend_client must provide a post_event(event) method"
            )

        self.object_detector = object_detector
        self.hand_tracker = hand_tracker
        self.session = session
        self.backend_client = backend_client

    @property
    def use_backend(self) -> bool:
        """Return True when backend mode is enabled."""
        return self.backend_client is not None

    def process_frame(
        self,
        frame: np.ndarray,
        source: str = "camera",
        captured_monotonic: float | None = None,
    ) -> Dict[str, Any]:
        """Process one OpenCV BGR frame."""

        if frame is None:
            raise ValueError(
                "process_frame received None frame"
            )

        if (
            not isinstance(frame, np.ndarray)
            or frame.ndim != 3
            or frame.shape[2] != 3
        ):
            raise ValueError(
                "process_frame expects an OpenCV BGR frame"
            )

        # Detect objects using YOLO.
        yolo_started = time.perf_counter()
        set_frame_timestamp = getattr(self.object_detector, "set_frame_timestamp", None)
        if callable(set_frame_timestamp) and captured_monotonic is not None:
            set_frame_timestamp(captured_monotonic)
        objects = self.object_detector.detect(frame)
        yolo_ms = (time.perf_counter() - yolo_started) * 1000.0

        # Detect hands using MediaPipe.
        mediapipe_started = time.perf_counter()
        hands = self.hand_tracker.process(frame) if self.hand_tracker is not None else []
        mediapipe_ms = (time.perf_counter() - mediapipe_started) * 1000.0

        # Convert MediaPipe normalized hand landmarks
        # into pixel-space hand centers.
        frame_height, frame_width = frame.shape[:2]

        for hand in hands:
            landmarks = hand.get("landmarks", [])

            if not landmarks:
                continue

            pixel_points = []

            for landmark in landmarks:
                try:
                    x = float(landmark["x"]) * frame_width
                    y = float(landmark["y"]) * frame_height
                    pixel_points.append((x, y))
                except (KeyError, TypeError, ValueError):
                    continue

            if pixel_points:
                hand["center"] = [
                    sum(point[0] for point in pixel_points)
                    / len(pixel_points),
                    sum(point[1] for point in pixel_points)
                    / len(pixel_points),
                ]

        apply_hand_context = getattr(self.object_detector, "apply_hand_context", None)
        if callable(apply_hand_context):
            apply_hand_context(objects, hands, frame.shape)

        # Create a perception event.
        event = PerceptionEvent(
            timestamp=datetime.now().isoformat(),
            source=source,
            objects=objects,
            hands=hands,
        )

        # Send perception into the mission decision system.
        # MODE A (local/offline, default): use the local session so
        # onboard operation and existing Phase 13 tests keep working.
        # MODE B (backend): POST the same PerceptionEvent to FastAPI
        # /api/mission/event, which is authoritative when the dashboard
        # backend is running. No decision logic is duplicated here.
        mission_started = time.perf_counter()
        if self.backend_client is not None:
            result = self.backend_client.post_event(event)
        else:
            result = self.session.process_event(event)
        mission_event_ms = (time.perf_counter() - mission_started) * 1000.0

        # Return the original frame as well as the
        # perception event and protocol decision.
        return {
            "frame": frame,
            "event": event,
            "result": result,
            "timings_ms": {
                "yolo_ms": round(yolo_ms, 2),
                "mediapipe_ms": round(mediapipe_ms, 2),
                "mission_event_ms": round(mission_event_ms, 2),
            },
        }

    def close(self) -> None:
        """Release the hand tracker if it supports close()."""

        close_method = getattr(
            self.hand_tracker,
            "close",
            None,
        )

        if callable(close_method):
            close_method()