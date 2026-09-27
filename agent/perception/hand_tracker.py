
"""MediaPipe Tasks hand tracker for ASTRA-GUARD Phase 6."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "hand_tracking"
    / "hand_landmarker.task"
)

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)

# MediaPipe hand landmark connections.
HAND_CONNECTIONS: Tuple[Tuple[int, int], ...] = (
    (0, 1),
    (0, 17),
    (1, 2),
    (1, 5),
    (2, 3),
    (3, 4),
    (5, 6),
    (5, 9),
    (6, 7),
    (7, 8),
    (9, 10),
    (9, 13),
    (10, 11),
    (11, 12),
    (13, 14),
    (13, 17),
    (14, 15),
    (15, 16),
    (17, 18),
    (18, 19),
    (19, 20),
)


class HandTrackerInitError(RuntimeError):
    """Raised when MediaPipe HandLandmarker cannot be initialized."""


def _to_legacy_result(result: Any) -> SimpleNamespace:
    """
    Convert MediaPipe Tasks HandLandmarkerResult into the internal
    structure expected by HandTracker.process().
    """

    hand_landmarks = getattr(result, "hand_landmarks", None) or []
    handedness = getattr(result, "handedness", None) or []

    multi_landmarks = [
        SimpleNamespace(landmark=list(points))
        for points in hand_landmarks
    ]

    multi_handedness = []

    for categories in handedness:
        category = categories[0] if categories else None

        if category is None:
            multi_handedness.append(
                SimpleNamespace(classification=[])
            )
            continue

        label = (
            getattr(category, "category_name", None)
            or getattr(category, "display_name", None)
            or "Unknown"
        )

        score = float(
            getattr(category, "score", 0.0) or 0.0
        )

        multi_handedness.append(
            SimpleNamespace(
                classification=[
                    SimpleNamespace(
                        label=str(label),
                        score=score,
                    )
                ]
            )
        )

    return SimpleNamespace(
        multi_hand_landmarks=multi_landmarks,
        multi_handedness=multi_handedness,
    )


class _TasksHandsAdapter:
    """Adapter exposing process() and close() for MediaPipe Tasks."""

    def __init__(self, landmarker: Any, mp_module: Any) -> None:
        self._landmarker = landmarker
        self._mp = mp_module
        self._last_ts_ms = -1

    def _next_timestamp_ms(self) -> int:
        """Return strictly increasing timestamps for VIDEO mode."""

        timestamp = int(time.monotonic() * 1000)

        if timestamp <= self._last_ts_ms:
            timestamp = self._last_ts_ms + 1

        self._last_ts_ms = timestamp

        return timestamp

    def process(self, rgb: np.ndarray) -> SimpleNamespace:
        """Run hand landmark detection on an RGB frame."""

        image = self._mp.Image(
            image_format=self._mp.ImageFormat.SRGB,
            data=np.ascontiguousarray(rgb),
        )

        result = self._landmarker.detect_for_video(
            image,
            self._next_timestamp_ms(),
        )

        return _to_legacy_result(result)

    def close(self) -> None:
        """Close the MediaPipe landmarker."""

        self._landmarker.close()


class HandTracker:
    """Wrapper around MediaPipe Tasks HandLandmarker."""

    def __init__(
        self,
        max_num_hands: int = 2,
        detection_confidence: float = 0.5,
        tracking_confidence: float = 0.5,
        model_path: Optional[Union[str, Path]] = None,
    ) -> None:

        self.max_num_hands = int(max_num_hands)
        self.detection_confidence = float(detection_confidence)
        self.tracking_confidence = float(tracking_confidence)

        self.model_path = (
            Path(model_path)
            if model_path
            else DEFAULT_MODEL_PATH
        )

        self._hands = None

        self._init_tracker()

    def _init_tracker(self) -> None:
        """Initialize MediaPipe Tasks HandLandmarker."""

        model = Path(self.model_path)

        if not model.is_file():
            raise HandTrackerInitError(
                f"Hand landmarker model not found: {model}\n"
                "Download it with:\n"
                "python scripts/download_hand_model.py"
            )

        try:
            model_data = model.read_bytes()
        except OSError as exc:
            raise HandTrackerInitError(
                f"Cannot read hand model '{model}': {exc}"
            ) from exc

        try:
            import mediapipe as mp
            from mediapipe.tasks import python as mp_python
            from mediapipe.tasks.python import vision
        except Exception as exc:
            raise HandTrackerInitError(
                "MediaPipe Tasks API is unavailable: "
                f"{exc}"
            ) from exc

        try:
            options = vision.HandLandmarkerOptions(
                base_options=mp_python.BaseOptions(
                    model_asset_buffer=model_data
                ),
                running_mode=vision.RunningMode.VIDEO,
                num_hands=self.max_num_hands,
                min_hand_detection_confidence=self.detection_confidence,
                min_tracking_confidence=self.tracking_confidence,
            )

            landmarker = vision.HandLandmarker.create_from_options(
                options
            )

        except Exception as exc:
            raise HandTrackerInitError(
                "MediaPipe HandLandmarker initialization failed: "
                f"{exc}"
            ) from exc

        self._hands = _TasksHandsAdapter(
            landmarker,
            mp,
        )

    def process(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Detect hands from an OpenCV BGR frame."""

        if frame is None:
            raise ValueError(
                "process received None frame"
            )

        if (
            not isinstance(frame, np.ndarray)
            or frame.ndim != 3
            or frame.shape[2] != 3
        ):
            raise ValueError(
                "process expects an OpenCV BGR frame"
            )

        if self._hands is None:
            raise HandTrackerInitError(
                "Hand tracker is closed or not initialized"
            )

        try:
            rgb = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB,
            )

            results = self._hands.process(rgb)

        except Exception as exc:
            raise RuntimeError(
                f"MediaPipe inference failed: {exc}"
            ) from exc

        hands: List[Dict[str, Any]] = []

        landmarks_list = (
            getattr(
                results,
                "multi_hand_landmarks",
                None,
            )
            or []
        )

        handed_list = (
            getattr(
                results,
                "multi_handedness",
                None,
            )
            or []
        )

        for index, landmark_group in enumerate(
            landmarks_list
        ):

            label = "Unknown"
            score = 0.0

            if index < len(handed_list):
                try:
                    category = (
                        handed_list[index]
                        .classification[0]
                    )

                    score = float(category.score)
                    label = str(category.label)

                except Exception:
                    pass

            points = []

            for point in getattr(
                landmark_group,
                "landmark",
                [],
            ):
                try:
                    points.append(
                        {
                            "x": float(point.x),
                            "y": float(point.y),
                            "z": float(point.z),
                        }
                    )
                except Exception:
                    continue

            hands.append(
                {
                    "hand_index": index,
                    "handedness": label,
                    "confidence": score,
                    "landmarks": points,
                }
            )

        return hands

    def draw_landmarks(
        self,
        frame: np.ndarray,
        hands: List[Dict[str, Any]],
        copy_frame: bool = True,
    ) -> np.ndarray:
        """Draw hand landmarks, copying the frame unless requested otherwise."""

        if frame is None:
            raise ValueError(
                "draw_landmarks received None frame"
            )

        annotated = frame.copy() if copy_frame else frame

        height, width = annotated.shape[:2]

        for hand in hands or []:

            points: List[
                Optional[Tuple[int, int]]
            ] = []

            for point in hand.get(
                "landmarks",
                [],
            ):

                try:
                    points.append(
                        (
                            int(
                                round(
                                    float(point["x"])
                                    * width
                                )
                            ),
                            int(
                                round(
                                    float(point["y"])
                                    * height
                                )
                            ),
                        )
                    )

                except Exception:
                    points.append(None)

            # Draw connections.
            for start, end in HAND_CONNECTIONS:

                if (
                    start < len(points)
                    and end < len(points)
                    and points[start]
                    and points[end]
                ):
                    cv2.line(
                        annotated,
                        points[start],
                        points[end],
                        (0, 255, 0),
                        2,
                    )

            # Draw landmarks.
            for point in points:

                if point:
                    cv2.circle(
                        annotated,
                        point,
                        3,
                        (0, 0, 255),
                        -1,
                    )

            label = str(
                hand.get(
                    "handedness",
                    "?",
                )
            )

            index = int(
                hand.get(
                    "hand_index",
                    0,
                )
            )

            if points and points[0]:

                origin = (
                    max(0, points[0][0]),
                    max(15, points[0][1] - 10),
                )

            else:

                origin = (
                    10,
                    30 + 25 * index,
                )

            cv2.putText(
                annotated,
                label,
                origin,
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 0, 0),
                2,
            )

        return annotated

    def close(self) -> None:
        """Release the MediaPipe hand tracker."""

        if self._hands is not None:

            try:
                self._hands.close()

            except Exception as exc:
                logger.warning(
                    "Hand tracker close failed: %s",
                    exc,
                )

            finally:
                self._hands = None
