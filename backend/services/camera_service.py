"""ASTRA-GUARD shared camera service (single-owner capture)."""

from __future__ import annotations

import threading
import time
from typing import Generator

import cv2
import numpy as np


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

_EXTERNAL_FRESH_SEC = 2.0
_FRAME_DELAY_SEC = 0.03
_JPEG_QUALITY = 80


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
        camera_index: int = 0,
        width: int = 640,
        height: int = 480,
    ) -> None:

        self.camera_index = int(camera_index)
        self.width = int(width)
        self.height = int(height)

        self._lock = threading.Condition()
        self._camera_lock = threading.Lock()

        self._latest_jpeg: bytes | None = None
        self._external_jpeg: bytes | None = None
        self._external_ts: float = 0.0

        self._capture_count = 0
        self._error: str | None = None

        self._camera = None
        self._thread: threading.Thread | None = None

        self._stop = threading.Event()

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
    ) -> bool:
        """Publish an externally captured JPEG frame."""

        if not jpeg:
            return False

        # Basic JPEG signature validation.
        if not jpeg.startswith(b"\xff\xd8"):
            return False

        with self._lock:
            self._external_jpeg = bytes(jpeg)
            self._external_ts = time.monotonic()
            self._latest_jpeg = self._external_jpeg
            self._capture_count += 1
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

        if self._thread is not None and self._thread.is_alive():
            return

        self._stop.clear()

        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
            name="astra-camera",
        )

        self._thread.start()

    def stop(self) -> None:
        """Stop the camera service and release the camera."""

        self._stop.set()

        with self._camera_lock:
            cam = self._camera
            self._camera = None

        if cam is not None:
            try:
                cam.release()
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

    # -----------------------------------------------------
    # LOCAL CAMERA
    # -----------------------------------------------------

    def _ensure_camera(self) -> bool:
        """Open the local camera if it is not already open."""

        with self._camera_lock:
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

                return True

            except Exception as exc:
                self._error = str(exc)
                self._camera = None
                return False

    def _release_camera(self) -> None:
        """Release the local camera safely."""

        with self._camera_lock:
            cam = self._camera
            self._camera = None

        if cam is not None:
            try:
                cam.release()
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
                    self._release_camera()
                    time.sleep(0.05)
                    continue

                # Open local camera if necessary.
                if not self._ensure_camera():
                    time.sleep(1.0)
                    continue

                # Read frame from the local camera.
                with self._camera_lock:
                    cam = self._camera

                    if cam is None:
                        continue

                    ok, frame = cam.read()

                if not ok or frame is None:
                    time.sleep(0.05)
                    continue

                jpeg = encode_bgr_to_jpeg(frame)

                if jpeg:
                    with self._lock:
                        self._latest_jpeg = jpeg
                        self._capture_count += 1
                        self._error = None
                        self._lock.notify_all()

                time.sleep(_FRAME_DELAY_SEC)

            except Exception as exc:
                self._error = str(exc)
                time.sleep(0.2)

    # -----------------------------------------------------
    # STATUS
    # -----------------------------------------------------

    def get_status(self) -> dict:
        """Return the current camera service status."""

        with self._lock:
            has_frame = self._latest_jpeg is not None
            capture_count = self._capture_count
            error = self._error
            width = self.width
            height = self.height

        with self._camera_lock:
            cam = self._camera

        try:
            cam_open = (
                cam is not None
                and bool(cam.is_opened())
            )
        except Exception:
            cam_open = False

        external = self._external_fresh()

        return {
            "connected": bool(has_frame or cam_open or external),
            "camera_open": cam_open,
            "external_stream": external,
            "has_frame": has_frame,
            "frames_captured": capture_count,
            "width": width,
            "height": height,
            "camera_index": self.camera_index,
            "error": error,
        }


# ---------------------------------------------------------
# MJPEG STREAM GENERATOR
# ---------------------------------------------------------

def mjpeg_generator() -> Generator[bytes, None, None]:
    """Stream each newly published JPEG, skipping duplicate and stale frames."""

    service = get_camera_service()
    last_sequence = -1

    while True:
        frame, sequence = service.wait_for_new_frame(last_sequence)

        if frame is None:
            frame = _placeholder_jpeg()

        if sequence == last_sequence:
            continue

        last_sequence = sequence
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n"
            b"Content-Length: "
            + str(len(frame)).encode()
            + b"\r\n\r\n"
            + frame
            + b"\r\n"
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