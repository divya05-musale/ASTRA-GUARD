"""ASTRA-GUARD shared camera service (single-owner capture)."""

from __future__ import annotations

import threading
import time
import os
import logging
from typing import Generator

import cv2
import numpy as np
from agent.perception.camera import assess_frame, normalize_camera_backend
from backend.core.config import get_settings


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

_EXTERNAL_FRESH_SEC = 2.0
_LOCAL_FRAME_FRESH_SEC = 2.0
_CAMERA_START_TIMEOUT_SEC = 5.0
_FRAME_DELAY_SEC = 0.03
_JPEG_QUALITY = 80
# A 640x480 q80 JPEG of a real scene is always larger than this. A JPEG of pure
# black compresses to almost nothing, so an unusually small payload is the cheap
# signal that lets us decode-and-confirm instead of trusting every upload.
_BLACK_SUSPECT_MAX_BYTES = 6144
logger = logging.getLogger(__name__)


def jpeg_is_black(jpeg: bytes) -> bool:
    """Detect an all-black JPEG without decoding ordinary frames.

    The live pipeline already refuses black frames at capture time; this is the
    second line of defence so a broken publisher cannot blank the dashboard.
    """

    if not jpeg or len(jpeg) > _BLACK_SUSPECT_MAX_BYTES:
        return False
    try:
        decoded = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
    except Exception:
        return False
    if decoded is None:
        return False
    return bool(assess_frame(decoded)["is_black"])


# ---------------------------------------------------------
# IMAGE HELPERS
# ---------------------------------------------------------

def _placeholder_jpeg(text: str = "CAMERA OFFLINE") -> bytes:
    """Generate a placeholder JPEG image."""

    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[:] = (16, 22, 38)

    cv2.putText(
        img,
        "ASTRA-GUARD",
        (160, 200),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (147, 197, 253),
        2,
        cv2.LINE_AA,
    )

    cv2.putText(
        img,
        text,
        (160, 260),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (148, 163, 184),
        2,
        cv2.LINE_AA,
    )

    ok, buf = cv2.imencode(
        ".jpg",
        img,
        [int(cv2.IMWRITE_JPEG_QUALITY), _JPEG_QUALITY],
    )

    return bytes(buf.tobytes()) if ok else b""


def encode_bgr_to_jpeg(
    frame: np.ndarray,
    quality: int = _JPEG_QUALITY,
) -> bytes | None:
    """Convert an OpenCV BGR frame into JPEG bytes."""

    try:
        if frame is None or frame.size == 0:
            return None

        ok, buf = cv2.imencode(
            ".jpg",
            frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)],
        )

        return bytes(buf.tobytes()) if ok else None

    except Exception:
        return None


# ---------------------------------------------------------
# CAMERA SERVICE
# ---------------------------------------------------------

class CameraService:
    """Shared camera service for local and external video frames."""

    def __init__(
        self,
        camera_index: int | None = None,
        width: int = 640,
        height: int = 480,
    ) -> None:

        configured_index = os.environ.get("ASTRA_GUARD_CAMERA_INDEX", "0")
        self.camera_index = int(configured_index if camera_index is None else camera_index)
        if self.camera_index < 0:
            raise ValueError("Camera index must be zero or greater.")
        self.camera_source = "laptop"
        self.camera_source_name = "Laptop Webcam"
        self.camera_backend = normalize_camera_backend(
            os.environ.get("ASTRA_GUARD_CAMERA_BACKEND", "dshow")
        )
        self._active_backend: str | None = None
        self.width = int(width)
        self.height = int(height)

        self._lock = threading.Condition()
        self._camera_lock = threading.Lock()
        self._lifecycle_lock = threading.RLock()

        self._latest_jpeg: bytes | None = None
        self._external_jpeg: bytes | None = None
        self._external_ts: float = 0.0

        self._capture_count = 0
        self._black_frames_rejected = 0
        self._last_reject_reason: str | None = None
        self._last_frame_ts: float = 0.0
        self._last_local_frame_ts = 0.0
        self._error: str | None = None
        self._last_logged_connected: bool | None = None

        self._camera = None
        self._thread: threading.Thread | None = None
        self._enabled = False

        self._stop = threading.Event()
        self._live_control_lock = threading.Lock()
        self._live_control_generation = 0
        self._live_control_request: dict | None = None
        self._live_control_result_generation = 0
        self._live_control_error: str | None = None

    # -----------------------------------------------------
    # FRAME PUBLISHING
    # -----------------------------------------------------

    def publish_frame_bgr(self, frame: np.ndarray) -> bool:
        """Publish an externally captured BGR frame."""

        jpeg = encode_bgr_to_jpeg(frame)

        if jpeg is None:
            return False

        return self.publish_external_jpeg(jpeg)

    def publish_external_jpeg(
        self,
        jpeg: bytes,
        width: int | None = None,
        height: int | None = None,
        camera_index: int | None = None,
        camera_source: str | None = None,
        camera_backend: str | None = None,
        camera_backend_requested: str | None = None,
        camera_source_name: str | None = None,
    ) -> bool:
        """Publish an externally captured JPEG frame."""

        if not jpeg:
            return False

        # Basic JPEG signature validation.
        if not jpeg.startswith(b"\xff\xd8"):
            return False

        if jpeg_is_black(jpeg):
            # A publisher feeding black pixels must not overwrite the last real
            # frame, otherwise the dashboard shows a dead camera as a live one.
            with self._lock:
                self._black_frames_rejected += 1
                self._last_reject_reason = (
                    "published frame contained no image data (all pixels black)"
                )
            return False

        with self._lock:
            self._external_jpeg = bytes(jpeg)
            self._external_ts = time.monotonic()
            self._latest_jpeg = self._external_jpeg
            self._capture_count += 1
            self._last_frame_ts = self._external_ts
            if camera_index is not None and int(camera_index) >= 0:
                self.camera_index = int(camera_index)
            if camera_source in {"laptop", "usb"}:
                self.camera_source = camera_source
                self.camera_source_name = camera_source_name or (
                    "USB External Camera" if camera_source == "usb" else "Laptop Webcam"
                )
            if camera_backend:
                self._active_backend = str(camera_backend).upper()
            if camera_backend_requested in {"auto", "dshow", "msmf"}:
                self.camera_backend = camera_backend_requested
            logger.debug("External camera frame published sequence=%d", self._capture_count)
            if width and width > 0:
                self.width = int(width)
            if height and height > 0:
                self.height = int(height)
            self._error = None
            self._lock.notify_all()

        return True

    # -----------------------------------------------------
    # FRAME RETRIEVAL
    # -----------------------------------------------------

    def get_jpeg(self) -> bytes | None:
        """Return the most recently available JPEG frame."""

        return self.get_latest_frame()[0]

    def get_latest_frame(self) -> tuple[bytes | None, int]:
        """Return the newest JPEG and its monotonically increasing version."""

        with self._lock:
            return self._latest_jpeg, self._capture_count

    def wait_for_new_frame(
        self,
        last_sequence: int,
        timeout: float = 0.5,
    ) -> tuple[bytes | None, int]:
        """Sleep until a new frame arrives or the stream should retry."""

        with self._lock:
            self._lock.wait_for(
                lambda: self._capture_count != last_sequence,
                timeout=timeout,
            )
            return self._latest_jpeg, self._capture_count

    def _external_fresh(self) -> bool:
        """Check whether an external frame was received recently."""

        with self._lock:
            return (
                self._external_jpeg is not None
                and (time.monotonic() - self._external_ts)
                < _EXTERNAL_FRESH_SEC
            )

    # -----------------------------------------------------
    # CAMERA LIFECYCLE
    # -----------------------------------------------------

    def ensure_started(self) -> None:
        """Start the background camera service."""
        settings = get_settings()
        if settings.is_cloud_mode() or not settings.ENABLE_LIVE_PROCESSOR:
            with self._lock:
                self._error = "Camera capture is disabled in cloud mode."
            self._enabled = False
            return

        with self._lifecycle_lock:
            if self._thread is not None and self._thread.is_alive():
                self._enabled = True
                return

            self._stop.clear()
            self._enabled = True
            with self._lock:
                self._error = None
            self._thread = threading.Thread(
                target=self._loop,
                daemon=True,
                name="astra-camera",
            )
            self._thread.start()

    def stop(self) -> None:
        """Stop the camera service and release the camera."""
        with self._lifecycle_lock:
            self._enabled = False
            self._stop.set()

            with self._camera_lock:
                cam = self._camera
                self._camera = None

            if cam is not None:
                try:
                    cam.release()
                    logger.info("Camera capture closed index=%d reason=service stop", self.camera_index)
                except Exception:
                    pass

            thread = self._thread
            if (
                thread is not None
                and thread.is_alive()
                and thread is not threading.current_thread()
            ):
                thread.join(timeout=2.0)

            self._thread = None
            external_jpeg = self._external_jpeg if self._external_fresh() else None
            with self._lock:
                self._latest_jpeg = external_jpeg
                self._last_local_frame_ts = 0.0
                self._lock.notify_all()

    def select_camera(
        self,
        camera_index: int,
        source: str,
        backend: str = "dshow",
        source_name: str | None = None,
    ) -> dict:
        """Switch the local camera device, restarting capture if it was running."""
        camera_index = int(camera_index)
        if camera_index < 0:
            raise ValueError("Camera index must be zero or greater.")
        if source not in {"laptop", "usb"}:
            raise ValueError("Camera source must be 'laptop' or 'usb'.")
        backend = normalize_camera_backend(backend)

        with self._lifecycle_lock:
            was_enabled = self._enabled
            previous = (
                self.camera_index,
                self.camera_source,
                self.camera_source_name,
                self.camera_backend,
            )
            requested_source_name = source_name or (
                "USB External Camera" if source == "usb" else "Laptop Webcam"
            )
            if (
                camera_index == self.camera_index
                and source == self.camera_source
                and backend == self.camera_backend
                and requested_source_name == self.camera_source_name
            ):
                return self.get_status()

            self.stop()
            self.camera_index = camera_index
            self.camera_source = source
            self.camera_source_name = requested_source_name
            self.camera_backend = backend
            self._active_backend = backend.upper()
            with self._lock:
                self._latest_jpeg = self._external_jpeg if self._external_fresh() else None
                self._last_local_frame_ts = 0.0
                self._error = None
                self._lock.notify_all()
            if was_enabled:
                started_at = time.monotonic()
                self.ensure_started()
                if not self.wait_for_local_frame(started_at, _CAMERA_START_TIMEOUT_SEC):
                    selection_error = self.get_status()["error"] or (
                        f"Camera index {camera_index} using {backend.upper()} did not produce a frame."
                    )
                    self.stop()
                    (
                        self.camera_index,
                        self.camera_source,
                        self.camera_source_name,
                        self.camera_backend,
                    ) = previous
                    self.ensure_started()
                    restored_at = time.monotonic()
                    restored = self.wait_for_local_frame(restored_at, _CAMERA_START_TIMEOUT_SEC)
                    if not restored:
                        selection_error = (
                            f"Camera switch failed: {selection_error}; previous camera could not be restored."
                        )
                    else:
                        selection_error = (
                            f"Camera switch failed: {selection_error}; previous camera restored."
                        )
                    raise RuntimeError(selection_error)
            return self.get_status()

    def request_live_camera_selection(
        self,
        camera_index: int,
        source: str,
        backend: str = "dshow",
        source_name: str | None = None,
    ) -> dict:
        """Queue a device change for the separate live-perception process."""
        camera_index = int(camera_index)
        if camera_index < 0:
            raise ValueError("Camera index must be zero or greater.")
        if source not in {"laptop", "usb"}:
            raise ValueError("Camera source must be 'laptop' or 'usb'.")
        backend = normalize_camera_backend(backend)

        with self._live_control_lock:
            self._live_control_generation += 1
            self._live_control_request = {
                "generation": self._live_control_generation,
                "camera_index": camera_index,
                "camera_source": source,
                "camera_backend": backend,
                "camera_source_name": source_name or (
                    "USB External Camera" if source == "usb" else "Laptop Webcam"
                ),
            }
            self._live_control_error = None
            return dict(self._live_control_request)

    def get_live_camera_control(self, after_generation: int = 0) -> dict | None:
        with self._live_control_lock:
            request = self._live_control_request
            if request is None or request["generation"] <= after_generation:
                return None
            return dict(request)

    def complete_live_camera_selection(self, generation: int, error: str | None = None) -> None:
        with self._live_control_lock:
            if generation != self._live_control_generation:
                return
            self._live_control_result_generation = generation
            self._live_control_error = error

    def wait_for_local_frame(self, started_at: float, timeout: float) -> bool:
        """Wait for a real local frame captured after camera startup."""
        with self._lock:
            self._lock.wait_for(
                lambda: (
                    self._last_local_frame_ts >= started_at
                    or self._error is not None
                    or self._stop.is_set()
                ),
                timeout=timeout,
            )
            return self._last_local_frame_ts >= started_at

    # -----------------------------------------------------
    # LOCAL CAMERA
    # -----------------------------------------------------

    def _ensure_camera(self) -> bool:
        """Open the local camera if it is not already open."""

        with self._camera_lock:
            if self._stop.is_set():
                return False

            if self._camera is not None:
                try:
                    if self._camera.is_opened():
                        return True
                except Exception:
                    pass

            try:
                from agent.perception.camera import Camera

                cam = Camera(
                    camera_index=self.camera_index,
                    width=self.width,
                    height=self.height,
                    backend=self.camera_backend,
                    source_name=self.camera_source_name,
                )

                cam.open()

                if not cam.is_opened():
                    try:
                        cam.release()
                    except Exception:
                        pass

                    self._error = "Unable to open camera."
                    self._camera = None
                    return False

                self._camera = cam
                self._error = None
                self._active_backend = getattr(cam, "backend_name", None) or self.camera_backend.upper()
                logger.info(
                    "Camera capture opened index=%d backend=%s",
                    self.camera_index,
                    getattr(cam, "backend_name", None),
                )

                return True

            except Exception as exc:
                with self._lock:
                    self._error = str(exc)
                    self._lock.notify_all()
                self._camera = None
                return False

    def _release_camera(self, reason: str = "capture loop") -> None:
        """Release the local camera safely."""

        with self._camera_lock:
            cam = self._camera
            self._camera = None

        if cam is not None:
            try:
                cam.release()
                logger.info("Camera capture closed index=%d reason=%s", self.camera_index, reason)
            except Exception:
                pass

    # -----------------------------------------------------
    # BACKGROUND CAPTURE LOOP
    # -----------------------------------------------------

    def _loop(self) -> None:
        """Capture local frames when no external stream is active."""

        while not self._stop.is_set():

            try:
                # External pipeline owns the webcam.
                if self._external_fresh():
                    self._release_camera("external frames are active")
                    time.sleep(0.05)
                    continue

                # Open local camera if necessary.
                if not self._ensure_camera():
                    with self._lock:
                        self._lock.notify_all()
                    time.sleep(1.0)
                    continue

                # Read frame from the local camera.
                with self._camera_lock:
                    cam = self._camera

                    if cam is None:
                        continue

                    ok, frame = cam.read()

                if not ok or frame is None:
                    with self._lock:
                        self._error = (
                            f"Camera at index {self.camera_index} is open but did not return a frame."
                        )
                        self._lock.notify_all()
                    self._release_camera("frame read failed")
                    time.sleep(0.05)
                    continue

                jpeg = encode_bgr_to_jpeg(frame)

                if jpeg:
                    with self._lock:
                        self._latest_jpeg = jpeg
                        self._capture_count += 1
                        self._last_local_frame_ts = time.monotonic()
                        self._error = None
                        self._lock.notify_all()
                        logger.debug(
                            "Local camera frame published index=%d sequence=%d",
                            self.camera_index,
                            self._capture_count,
                        )

                time.sleep(_FRAME_DELAY_SEC)

            except Exception as exc:
                with self._lock:
                    self._error = str(exc)
                    self._lock.notify_all()
                time.sleep(0.2)

    # -----------------------------------------------------
    # STATUS
    # -----------------------------------------------------

    def get_status(self) -> dict:
        """Return the current camera service status."""
        settings = get_settings()
        if settings.is_cloud_mode() or not settings.ENABLE_LIVE_PROCESSOR:
            with self._lock:
                now = time.monotonic()
                external = (
                    self._external_jpeg is not None
                    and now - self._external_ts < _EXTERNAL_FRESH_SEC
                )
                frame_age = max(0.0, now - self._external_ts) if external else None
                error = None if external else "Camera capture is disabled in cloud mode."
            return {
                "connected": external,
                "enabled": external,
                "capture_running": False,
                "camera_open": False,
                "external_stream": external,
                "has_frame": external,
                "frame_age_seconds": frame_age,
                "frames_captured": self._capture_count,
                "width": self.width,
                "height": self.height,
                "camera_index": self.camera_index,
                "camera_source": self.camera_source,
                "camera_source_name": self.camera_source_name,
                "camera_backend": None,
                "camera_backend_requested": self.camera_backend,
                "camera_switch_pending": False,
                "camera_switch_error": None,
                "backend": None,
                "error": error,
                "cloud_mode": True,
            }

        with self._lifecycle_lock:
            capture_running = self._thread is not None and self._thread.is_alive()

        with self._lock:
            now = time.monotonic()
            local_frame_fresh = (
                self._last_local_frame_ts > 0
                and now - self._last_local_frame_ts < _LOCAL_FRAME_FRESH_SEC
            )
            external = (
                self._external_jpeg is not None
                and now - self._external_ts < _EXTERNAL_FRESH_SEC
            )
            has_frame = local_frame_fresh or external
            capture_count = self._capture_count
            error = self._error
            width = self.width
            height = self.height
            enabled = self._enabled
            frame_age = (
                max(0.0, now - max(self._last_local_frame_ts, self._external_ts))
                if has_frame
                else None
            )

        with self._camera_lock:
            cam = self._camera

        try:
            cam_open = (
                cam is not None
                and bool(cam.is_opened())
            )
        except Exception:
            cam_open = False

        connected = bool(external or (enabled and cam_open and local_frame_fresh))
        active_backend = (
            getattr(cam, "backend_name", None) or self._active_backend
            if cam_open or external
            else None
        )
        with self._lock:
            if connected != self._last_logged_connected:
                logger.info(
                    "Camera connection changed connected=%s index=%d frames=%d local_fresh=%s external_fresh=%s",
                    connected,
                    self.camera_index,
                    capture_count,
                    local_frame_fresh,
                    external,
                )
                self._last_logged_connected = connected

        return {
            "connected": connected,
            "enabled": enabled,
            "capture_running": capture_running,
            "camera_open": cam_open,
            "external_stream": external,
            "has_frame": has_frame,
            "frame_age_seconds": frame_age,
            "frames_captured": capture_count,
            "width": width,
            "height": height,
            "camera_index": self.camera_index,
            "camera_source": self.camera_source,
            "camera_source_name": self.camera_source_name,
            "camera_backend": active_backend,
            "camera_backend_requested": self.camera_backend,
            "camera_switch_pending": self._live_control_result_generation < self._live_control_generation,
            "camera_switch_error": self._live_control_error,
            "backend": getattr(cam, "backend_name", None),
            "error": error,
            "cloud_mode": False,
        }


# ---------------------------------------------------------
# MJPEG STREAM GENERATOR
# ---------------------------------------------------------

def mjpeg_generator() -> Generator[bytes, None, None]:
    """Stream each newly published JPEG, skipping duplicate and stale frames."""

    service = get_camera_service()
    last_sequence = -1
    frames_sent = 0
    started_at = time.monotonic()
    logger.info("MJPEG stream generator started")

    try:
        while True:
            frame, sequence = service.wait_for_new_frame(last_sequence)

            if frame is None:
                frame = _placeholder_jpeg()

            if sequence == last_sequence:
                continue

            last_sequence = sequence
            frames_sent += 1
            if frames_sent % 120 == 0:
                logger.debug(
                    "MJPEG stream progress frames_sent=%d latest_sequence=%d",
                    frames_sent,
                    sequence,
                )
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"Content-Length: "
                + str(len(frame)).encode()
                + b"\r\n\r\n"
                + frame
                + b"\r\n"
            )
    finally:
        logger.info(
            "MJPEG stream generator closed duration_seconds=%.2f frames_sent=%d",
            time.monotonic() - started_at,
            frames_sent,
        )



# ---------------------------------------------------------
# SHARED SERVICE INSTANCE
# ---------------------------------------------------------

_service: CameraService | None = None
_service_lock = threading.Lock()


def get_camera_service() -> CameraService:
    """Return the shared camera service instance."""

    global _service

    if _service is None:
        with _service_lock:
            if _service is None:
                _service = CameraService()

    return _service


def stop_camera_service() -> None:
    """Release the shared camera when the backend shuts down."""
    if _service is not None:
        _service.stop()