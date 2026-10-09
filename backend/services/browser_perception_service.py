"""Process browser-uploaded frames through the existing live perception stack."""

from __future__ import annotations

import threading
import time
import logging
from pathlib import Path
from typing import Any, Dict

import numpy as np

from agent.perception.experiment_object_detector import ExperimentObjectDetector
from agent.perception.hand_tracker import HandTracker
from agent.perception.live_processor import LivePerceptionProcessor
from agent.perception.object_detector import ObjectDetector
from backend.core.config import get_settings
from backend.services.mission_service import get_mission_service
from backend.services.performance_service import get_performance_monitor


_DETECTION_FRESH_SECONDS = 3.0
logger = logging.getLogger(__name__)


class BrowserPerceptionService:
    """Own one lazy YOLO/MediaPipe processor for frames received over HTTP."""

    def __init__(self) -> None:
        self._processing_lock = threading.Lock()
        self._status_lock = threading.Lock()
        self._processor: LivePerceptionProcessor | None = None
        self._object_detector: ExperimentObjectDetector | None = None
        self._hand_tracker: HandTracker | None = None
        self._initialization_error: str | None = None
        self._mediapipe_error: str | None = None
        self._last_error: str | None = None
        self._last_frame_at: float | None = None
        self._frames_processed = 0
        self._last_object_count = 0
        self._last_hand_count = 0
        self._last_objects: list[dict[str, Any]] = []
        self._last_hands: list[dict[str, Any]] = []
        self._processing = False

    def _ensure_processor(self) -> LivePerceptionProcessor:
        if self._processor is not None:
            return self._processor
        if self._initialization_error:
            raise RuntimeError(self._initialization_error)

        settings = get_settings()
        model_path = Path(settings.YOLO_MODEL)
        if not model_path.is_absolute():
            model_path = settings.PROJECT_ROOT / model_path

        mission_service = get_mission_service()
        try:
            base_detector = ObjectDetector(
                model_path=str(model_path),
                confidence_threshold=settings.YOLO_CONFIDENCE,
            )
            object_detector = ExperimentObjectDetector(
                base_detector,
                mission_service._protocol_path,
                protocol_client=mission_service,
            )
        except Exception as exc:
            with self._status_lock:
                self._initialization_error = str(exc)
            raise RuntimeError(self._initialization_error) from exc

        hand_tracker = None
        mediapipe_error = None
        if settings.ENABLE_MEDIAPIPE:
            try:
                hand_tracker = HandTracker()
            except Exception as exc:
                mediapipe_error = str(exc)
                logger.warning("Browser hand detection is unavailable: %s", exc)
        else:
            mediapipe_error = "MediaPipe hand tracking is disabled by configuration."

        try:
            self._object_detector = object_detector
            self._hand_tracker = hand_tracker
            processor = LivePerceptionProcessor(
                object_detector,
                hand_tracker,
                mission_service,
            )
            with self._status_lock:
                self._processor = processor
                self._mediapipe_error = mediapipe_error
        except Exception as exc:
            with self._status_lock:
                self._initialization_error = str(exc)
            raise RuntimeError(self._initialization_error) from exc
        return processor

    def process_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """Run one uploaded BGR frame through YOLO, MediaPipe, and mission logic."""
        if (
            not isinstance(frame, np.ndarray)
            or frame.ndim != 3
            or frame.shape[2] != 3
            or frame.size == 0
        ):
            raise ValueError("Browser frame must decode to a non-empty BGR image.")

        with self._processing_lock:
            with self._status_lock:
                self._processing = True
            started = time.perf_counter()
            try:
                processor = self._ensure_processor()
                processed = processor.process_frame(frame, source="camera")
                event = processed["event"]
                timings = dict(processed.get("timings_ms") or {})
                timings["process_frame_ms"] = round((time.perf_counter() - started) * 1000.0, 2)
                get_performance_monitor().record_frame(timings)

                with self._status_lock:
                    self._frames_processed += 1
                    self._last_object_count = len(event.objects)
                    self._last_hand_count = len(event.hands)
                    self._last_objects = [dict(item) for item in event.objects]
                    self._last_hands = [dict(item) for item in event.hands]
                    self._last_frame_at = time.monotonic()
                    self._last_error = None
                return {
                    "event": event.to_dict(),
                    "result": processed["result"],
                    "timings_ms": timings,
                    "frames_processed": self._frames_processed,
                }
            except Exception as exc:
                with self._status_lock:
                    self._last_error = str(exc)
                raise
            finally:
                with self._status_lock:
                    self._processing = False

    def reset_processor(self) -> None:
        """Discard the processor bound to the previously selected mission."""
        with self._processing_lock:
            hand_tracker = self._hand_tracker
            with self._status_lock:
                self._processor = None
                self._object_detector = None
                self._hand_tracker = None
                self._initialization_error = None
                self._mediapipe_error = None
                self._last_error = None
                self._last_frame_at = None
                self._frames_processed = 0
                self._last_object_count = 0
                self._last_hand_count = 0
                self._last_objects = []
                self._last_hands = []
                self._processing = False
            if hand_tracker is not None:
                try:
                    hand_tracker.close()
                except Exception:
                    logger.exception("Failed to close MediaPipe tracker during experiment switch")

    def get_status(self) -> Dict[str, Any]:
        with self._status_lock:
            fresh = (
                self._last_frame_at is not None
                and time.monotonic() - self._last_frame_at < _DETECTION_FRESH_SECONDS
            )
            processing = self._processing
            processor_initialized = self._processor is not None
            error = self._last_error or self._initialization_error
            mediapipe_error = self._mediapipe_error
            last_object_count = self._last_object_count
            last_hand_count = self._last_hand_count
            latest_objects = [dict(item) for item in self._last_objects]
            latest_hands = [dict(item) for item in self._last_hands]
            frames_processed = self._frames_processed
            if error:
                yolo_status = "ERROR"
                mediapipe_status = "ERROR"
            elif processor_initialized:
                yolo_status = "ONLINE"
                mediapipe_status = "ONLINE" if self._hand_tracker is not None else "UNAVAILABLE"
            else:
                yolo_status = "IDLE"
                mediapipe_status = "IDLE"
            processor_status = (
                "ERROR" if error else "PROCESSING" if processing
                else "READY" if processor_initialized else "IDLE"
            )

        try:
            mission_status = get_mission_service().get_status()
            mission_engine_status = "ONLINE" if isinstance(mission_status, dict) else "ERROR"
        except Exception:
            mission_engine_status = "ERROR"

        return {
            "inference_active": bool(fresh),
            "frame_publishing": bool(fresh),
            "detections_fresh": bool(fresh),
            "last_object_count": last_object_count,
            "last_hand_count": last_hand_count,
            "latest_objects": latest_objects,
            "latest_hands": latest_hands,
            "frames_processed": frames_processed,
            "processing": processing,
            "processor_status": processor_status,
            "yolo_status": yolo_status,
            "mediapipe_status": mediapipe_status,
            "mission_engine_status": mission_engine_status,
            "error": error,
            "mediapipe_error": mediapipe_error,
        }


_service: BrowserPerceptionService | None = None
_service_lock = threading.Lock()


def get_browser_perception_service() -> BrowserPerceptionService:
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                _service = BrowserPerceptionService()
    return _service