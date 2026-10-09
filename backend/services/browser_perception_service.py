"""Process browser-uploaded frames through the existing live perception stack."""

from __future__ import annotations

import threading
import time
import logging
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from queue import Empty, Full, Queue
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


class FrameQueueFullError(RuntimeError):
    """Raised when the bounded browser-frame queue cannot accept another frame."""


class BrowserPerceptionService:
    """Own one lazy YOLO/MediaPipe processor for frames received over HTTP."""

    def __init__(self) -> None:
        self._processing_lock = threading.Lock()
        self._status_lock = threading.Lock()
        self._worker_start_lock = threading.Lock()
        self._frame_queue: Queue[tuple[int, np.ndarray, int]] = Queue(maxsize=1)
        self._worker: threading.Thread | None = None
        self._generation = 0
        self._next_frame_id = 1
        self._processor: LivePerceptionProcessor | None = None
        self._object_detector: ExperimentObjectDetector | None = None
        self._hand_tracker: HandTracker | None = None
        self._initialization_error: str | None = None
        self._mediapipe_error: str | None = None
        self._last_error: str | None = None
        self._last_frame_at: float | None = None
        self._last_received_at: str | None = None
        self._last_processed_frame_id: int | None = None
        self._active_frame_id: int | None = None
        self._latest_event: dict[str, Any] | None = None
        self._latest_result: Any = None
        self._latest_timings_ms: dict[str, Any] = {}
        self._frames_received = 0
        self._frames_accepted = 0
        self._frames_processed = 0
        self._frames_failed = 0
        self._frames_rejected = 0
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

    @staticmethod
    def _validate_frame(frame: np.ndarray) -> None:
        if (
            not isinstance(frame, np.ndarray)
            or frame.ndim != 3
            or frame.shape[2] != 3
            or frame.size == 0
        ):
            raise ValueError("Browser frame must decode to a non-empty BGR image.")

    def _ensure_worker(self) -> None:
        with self._worker_start_lock:
            if self._worker is None or not self._worker.is_alive():
                self._worker = threading.Thread(
                    target=self._worker_loop,
                    daemon=True,
                    name="astra-browser-perception",
                )
                self._worker.start()

    def enqueue_frame(self, frame: np.ndarray) -> Dict[str, int]:
        """Accept one decoded frame for bounded background processing."""
        self._validate_frame(frame)
        self._ensure_worker()
        with self._status_lock:
            self._frames_received += 1
            self._last_received_at = datetime.now(timezone.utc).isoformat()
            frame_id = self._next_frame_id
            self._next_frame_id += 1
            try:
                self._frame_queue.put_nowait((frame_id, frame.copy(), self._generation))
            except Full as exc:
                self._frames_rejected += 1
                logger.warning(
                    "Browser frame rejected: processing queue full frame_id=%d queue_depth=%d",
                    frame_id,
                    self._frame_queue.qsize(),
                )
                raise FrameQueueFullError("Browser frame processing queue is full.") from exc
            self._frames_accepted += 1
            logger.debug(
                "Browser frame accepted frame_id=%d width=%d height=%d queue_depth=%d",
                frame_id,
                frame.shape[1],
                frame.shape[0],
                self._frame_queue.qsize(),
            )
            return {
                "frame_id": frame_id,
                "frames_received": self._frames_received,
                "frames_accepted": self._frames_accepted,
                "frames_processed": self._frames_processed,
                "queue_depth": self._frame_queue.qsize(),
            }

    def _worker_loop(self) -> None:
        while True:
            frame_id, frame, generation = self._frame_queue.get()
            try:
                with self._processing_lock:
                    with self._status_lock:
                        if generation != self._generation:
                            continue
                        self._active_frame_id = frame_id
                    started = time.perf_counter()
                    logger.debug("Browser frame inference started frame_id=%d", frame_id)
                    try:
                        processed = self._process_frame_locked(frame)
                        with self._status_lock:
                            self._last_processed_frame_id = frame_id
                        logger.debug(
                            "Browser frame inference completed frame_id=%d duration_ms=%.2f detections=%d",
                            frame_id,
                            (time.perf_counter() - started) * 1000.0,
                            len(processed["event"].objects),
                        )
                    except Exception:
                        with self._status_lock:
                            self._frames_failed += 1
                        logger.exception("Browser frame processing failed frame_id=%d", frame_id)
            finally:
                with self._status_lock:
                    if self._active_frame_id == frame_id:
                        self._active_frame_id = None
                self._frame_queue.task_done()

    def process_frame(self, frame: np.ndarray) -> Dict[str, Any]:
        """Synchronously process one BGR frame for local callers and tests."""
        self._validate_frame(frame)
        with self._processing_lock:
            return self._process_frame_locked(frame)

    def _process_frame_locked(self, frame: np.ndarray) -> Dict[str, Any]:
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
                self._last_objects = deepcopy(event.objects)
                self._last_hands = deepcopy(event.hands)
                self._latest_event = event.to_dict()
                self._latest_result = deepcopy(processed["result"])
                self._latest_timings_ms = dict(timings)
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
                self._generation += 1
                while True:
                    try:
                        self._frame_queue.get_nowait()
                        self._frame_queue.task_done()
                    except Empty:
                        break
                self._processor = None
                self._object_detector = None
                self._hand_tracker = None
                self._initialization_error = None
                self._mediapipe_error = None
                self._last_error = None
                self._last_frame_at = None
                self._last_received_at = None
                self._last_processed_frame_id = None
                self._active_frame_id = None
                self._latest_event = None
                self._latest_result = None
                self._latest_timings_ms = {}
                self._frames_received = 0
                self._frames_accepted = 0
                self._frames_processed = 0
                self._frames_failed = 0
                self._frames_rejected = 0
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
            queue_depth = self._frame_queue.qsize()
            frames_received = self._frames_received
            frames_accepted = self._frames_accepted
            frames_failed = self._frames_failed
            frames_rejected = self._frames_rejected
            active_frame_id = self._active_frame_id
            last_processed_frame_id = self._last_processed_frame_id
            last_received_at = self._last_received_at
            latest_event = deepcopy(self._latest_event)
            latest_result = deepcopy(self._latest_result)
            latest_timings_ms = dict(self._latest_timings_ms)
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
            elif processing:
                yolo_status = "INITIALIZING"
                mediapipe_status = "INITIALIZING"
            else:
                yolo_status = "IDLE"
                mediapipe_status = "IDLE"
            processor_status = (
                "ERROR" if error else "PROCESSING" if processing
                else "QUEUED" if queue_depth
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
            "frames_received": frames_received,
            "frames_accepted": frames_accepted,
            "frames_failed": frames_failed,
            "frames_rejected": frames_rejected,
            "queue_depth": queue_depth,
            "active_frame_id": active_frame_id,
            "last_processed_frame_id": last_processed_frame_id,
            "last_received_at": last_received_at,
            "latest_event": latest_event,
            "latest_result": latest_result,
            "latest_timings_ms": latest_timings_ms,
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