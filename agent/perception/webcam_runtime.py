"""
Phase 7.4 Step 3 - Real webcam runtime.

Connects the real OpenCV webcam to the existing
LivePerceptionProcessor.

Single camera owner rule:
This runtime delegates capture to agent.perception.camera.Camera,
the ONE place in the codebase that calls cv2.VideoCapture.
CameraService (backend) never opens the device directly either —
it reuses the same Camera wrapper only when no external pipeline
is publishing frames.

This module does not contain protocol logic.
It only handles webcam capture and frame processing.
Publishes annotated frames to the shared CameraService so the
dashboard's /api/camera/stream endpoint shows the live view.
"""

from __future__ import annotations

import inspect
import threading
import time
from typing import Any, Callable, Dict, Optional

import cv2

from agent.perception.camera import Camera
from agent.perception.live_processor import LivePerceptionProcessor


class WebcamRuntime:
    """Run ASTRA-GUARD perception on a live webcam."""

    def __init__(
        self,
        processor: LivePerceptionProcessor,
        camera_index: int = 0,
        width: int = 640,
        height: int = 480,
        publish_to_backend: bool = True,
    ) -> None:

        if not hasattr(processor, "process_frame"):
            raise TypeError(
                "processor must provide a process_frame(frame) method"
            )

        self.processor = processor
        try:
            parameters = inspect.signature(processor.process_frame).parameters.values()
            self._processor_accepts_capture_timestamp = any(
                parameter.name == "captured_monotonic"
                or parameter.kind == inspect.Parameter.VAR_KEYWORD
                for parameter in parameters
            )
        except (TypeError, ValueError):
            self._processor_accepts_capture_timestamp = False
        self.camera_index = int(camera_index)
        self.width = int(width)
        self.height = int(height)
        self.publish_to_backend = publish_to_backend

        self.capture: Optional[Camera] = None
        self._stopped = False
        self._frame_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self._capture_stop = threading.Event()
        self._frame_condition = threading.Condition()
        self._latest_frame = None
        self._capture_sequence = 0
        self._processed_sequence = 0
        self._capture_thread: threading.Thread | None = None
        self._latest_capture_monotonic = 0.0
        self._last_read_capture_monotonic = 0.0
        self._capture_window_started = time.monotonic()
        self._capture_window_frames = 0
        self.capture_fps = 0.0

    def set_frame_callback(self, cb: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback invoked after each frame is processed."""
        self._frame_callback = cb

    def open(self) -> None:
        """Open the webcam via the shared Camera wrapper."""

        camera = Camera(
            camera_index=self.camera_index,
            width=self.width,
            height=self.height,
        )
        camera.open()
        self.capture = camera
        self._capture_stop.clear()
        self._capture_thread = threading.Thread(
            target=self._capture_latest,
            daemon=True,
            name="astra-frame-capture",
        )
        self._capture_thread.start()

    def _capture_latest(self) -> None:
        """Drain camera frames into a one-frame latest-value mailbox."""

        while not self._capture_stop.is_set():
            camera = self.capture
            if camera is None:
                break

            success, frame = camera.read()
            if not success or frame is None:
                self._capture_stop.wait(0.005)
                continue

            captured_at = time.monotonic()
            with self._frame_condition:
                self._latest_frame = frame
                self._capture_sequence += 1
                self._latest_capture_monotonic = captured_at
                self._capture_window_frames += 1
                elapsed = captured_at - self._capture_window_started
                if elapsed >= 1.0:
                    self.capture_fps = self._capture_window_frames / elapsed
                    self._capture_window_frames = 0
                    self._capture_window_started = captured_at
                self._frame_condition.notify_all()

    def read_frame(self):
        """Read one frame from the webcam."""

        if self.capture is None:
            raise RuntimeError(
                "Webcam is not open. Call open() first."
            )

        if self._capture_thread is not None:
            with self._frame_condition:
                available = self._frame_condition.wait_for(
                    lambda: (
                        self._capture_sequence > self._processed_sequence
                        or self._capture_stop.is_set()
                    ),
                    timeout=1.0,
                )
                if not available or self._latest_frame is None:
                    raise RuntimeError("Unable to read frame from webcam")
                frame = self._latest_frame
                self._last_read_capture_monotonic = self._latest_capture_monotonic
                self._processed_sequence = self._capture_sequence
            return frame

        success, frame = self.capture.read()

        if not success or frame is None:
            raise RuntimeError(
                "Unable to read frame from webcam"
            )

        self._last_read_capture_monotonic = time.monotonic()
        return frame

    def _publish_annotated(self, result: Dict[str, Any]) -> None:
        """Push annotated frame to CameraService so dashboard can stream it."""
        if not self.publish_to_backend:
            return
        annotated = result.get("annotated")
        if annotated is None:
            annotated = result.get("frame")
        if annotated is None:
            return
        try:
            from backend.services.camera_service import get_camera_service
            svc = get_camera_service()
            svc.publish_frame_bgr(annotated)
        except Exception:
            pass

    def process_once(self) -> Dict[str, Any]:
        """Capture and process exactly one webcam frame."""

        frame = self.read_frame()

        if self._processor_accepts_capture_timestamp:
            result = self.processor.process_frame(
                frame,
                captured_monotonic=self._last_read_capture_monotonic,
            )
        else:
            result = self.processor.process_frame(frame)
        result["capture_fps"] = round(self.capture_fps, 2)
        result["capture_monotonic"] = self._last_read_capture_monotonic

        self._publish_annotated(result)

        if self._frame_callback is not None:
            try:
                self._frame_callback(result)
            except Exception:
                pass

        return result

    def release(self) -> None:
        """Release the webcam."""

        self._stopped = True
        self._capture_stop.set()
        with self._frame_condition:
            self._frame_condition.notify_all()

        capture_thread = self._capture_thread
        if capture_thread is not None and capture_thread.is_alive():
            capture_thread.join(timeout=1.0)
        self._capture_thread = None

        camera = self.capture
        self.capture = None
        if camera is not None:
            camera.release()

        with self._frame_condition:
            self._latest_frame = None
            self._processed_sequence = self._capture_sequence

    def run(self) -> None:
        """Run the live webcam loop.

        Press Q to stop the runtime.
        """

        self.open()
        self._stopped = False

        try:
            while not self._stopped:

                try:
                    result = self.process_once()
                except RuntimeError:
                    cv2.waitKey(100)
                    continue

                frame = result.get("annotated", result.get("frame"))

                if frame is not None:
                    try:
                        cv2.imshow("ASTRA-GUARD", frame)
                    except Exception:
                        pass

                key = cv2.waitKey(1) & 0xFF

                if key == ord("q"):
                    break

        finally:
            self.release()
            try:
                cv2.destroyAllWindows()
            except Exception:
                pass
