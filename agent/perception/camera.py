"""Reusable OpenCV webcam capture layer for ASTRA-GUARD (Phase 5).

No object detection here. Frames stay in BGR. All processing is local.
"""
from __future__ import annotations

import logging
import os
import tempfile
import threading
from typing import Any, Dict, Iterable, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)
_CAMERA_LOCKS: set[str] = set()
_CAMERA_LOCKS_GUARD = threading.Lock()

CAMERA_BACKENDS = {
    "auto": (cv2.CAP_ANY, "AUTO"),
    "dshow": (cv2.CAP_DSHOW, "DirectShow"),
    "msmf": (cv2.CAP_MSMF, "Media Foundation"),
}
BACKEND_FALLBACK_ORDER = ["dshow", "msmf", "auto"]
BLACK_FRAME_MAX_MEAN = float(os.environ.get("ASTRA_GUARD_CAMERA_BLACK_MAX_MEAN", "3.0"))
BLACK_FRAME_MAX_STD = float(os.environ.get("ASTRA_GUARD_CAMERA_BLACK_MAX_STD", "1.5"))


def normalize_camera_backend(backend: str) -> str:
    value = str(backend).strip().lower()
    if value not in CAMERA_BACKENDS:
        raise ValueError("Camera backend must be 'auto', 'dshow', or 'msmf'.")
    return value


def assess_frame(frame: Optional[np.ndarray]) -> Dict[str, Any]:
    """Measure an OpenCV frame so black/empty captures can be detected.

    Returns mean/std/max statistics plus an ``is_black`` flag. Never raises.
    """

    if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
        return {
            "valid": False,
            "is_black": True,
            "reason": "frame is None or empty",
            "mean": 0.0,
            "std": 0.0,
            "max": 0,
            "shape": None,
        }

    try:
        mean = float(frame.mean())
        std = float(frame.std())
        peak = int(frame.max())
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        return {
            "valid": False,
            "is_black": True,
            "reason": f"could not measure frame: {exc}",
            "mean": 0.0,
            "std": 0.0,
            "max": 0,
            "shape": list(frame.shape),
        }

    is_black = mean <= BLACK_FRAME_MAX_MEAN and std <= BLACK_FRAME_MAX_STD
    return {
        "valid": not is_black,
        "is_black": is_black,
        "reason": "frame contains no image data (all pixels zero)" if is_black else None,
        "mean": round(mean, 3),
        "std": round(std, 3),
        "max": peak,
        "shape": list(frame.shape),
    }


def is_black_frame(frame: Optional[np.ndarray]) -> bool:
    """True when a frame carries no image data (device returned pure black)."""
    return assess_frame(frame)["is_black"]


class CameraOpenError(RuntimeError):
    """Raised when the webcam cannot be opened."""


class FrameReadError(RuntimeError):
    """Raised when a frame cannot be read from an opened camera."""


class CameraUnusableError(CameraOpenError):
    """Raised when a device opens but never delivers a usable (non-black) frame."""


class Camera:
    """Thin reusable wrapper around cv2.VideoCapture."""

    BACKENDS = CAMERA_BACKENDS

    @classmethod
    def normalize_backend(cls, backend: str) -> str:
        return normalize_camera_backend(backend)

    def __init__(self, camera_index: int = 0, width: int = 1280,
                 height: int = 720, fps: int = 30, backend: str = "dshow",
                 source_name: str | None = None,
                 validate_frames: bool = True,
                 verify_on_open: bool = True,
                 backend_fallback: bool = True,
                 verify_frames: int = 12) -> None:
        self.camera_index = int(camera_index)
        self.backend = self.normalize_backend(backend)
        self.requested_backend = self.backend
        self.source_name = str(source_name or "camera")
        self.requested_width = int(width)
        self.requested_height = int(height)
        self.requested_fps = float(fps)
        self.validate_frames = bool(validate_frames)
        self.verify_on_open = bool(verify_on_open)
        self.backend_fallback = bool(backend_fallback)
        self.verify_frames = max(1, int(verify_frames))
        self._cap: Optional[cv2.VideoCapture] = None
        self.backend_name: Optional[str] = None
        self._device_lock = None
        self._device_lock_path = os.path.join(
            tempfile.gettempdir(),
            f"astra-guard-camera-{self.camera_index}.lock",
        )
        self.frames_read = 0
        self.black_frames = 0
        self.consecutive_black_frames = 0
        self.last_error: Optional[str] = None
        self.last_frame_quality: Optional[Dict[str, Any]] = None

    def _acquire_device_lock(self) -> None:
        with _CAMERA_LOCKS_GUARD:
            if self._device_lock_path in _CAMERA_LOCKS:
                raise CameraOpenError(
                    f"Camera at index {self.camera_index} is already owned by ASTRA-GUARD."
                )
            _CAMERA_LOCKS.add(self._device_lock_path)

        handle = None
        try:
            handle = open(self._device_lock_path, "a+b")
            if os.name == "nt":
                import msvcrt

                handle.seek(0, os.SEEK_END)
                if handle.tell() == 0:
                    handle.write(b"\0")
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if handle is not None:
                handle.close()
            with _CAMERA_LOCKS_GUARD:
                _CAMERA_LOCKS.discard(self._device_lock_path)
            raise CameraOpenError(
                f"Camera at index {self.camera_index} is already owned by ASTRA-GUARD."
            ) from exc
        self._device_lock = handle

    def _release_device_lock(self) -> None:
        handle = self._device_lock
        self._device_lock = None
        if handle is not None:
            try:
                if os.name == "nt":
                    import msvcrt

                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            finally:
                handle.close()
        with _CAMERA_LOCKS_GUARD:
            _CAMERA_LOCKS.discard(self._device_lock_path)

    def open(self) -> "Camera":
        backends = [self.backend]
        if self.backend_fallback:
            for backend in BACKEND_FALLBACK_ORDER:
                if backend not in backends:
                    backends.append(backend)

        last_error: Optional[str] = None
        for backend in backends:
            try:
                self._acquire_device_lock()
                api, label = CAMERA_BACKENDS[backend]
                cap = cv2.VideoCapture(self.camera_index, api)
                if cap is None or not cap.isOpened():
                    if cap is not None:
                        try:
                            cap.release()
                        except Exception:
                            pass
                    self._release_device_lock()
                    last_error = f"{label} could not open the device."
                    continue

                try:
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.requested_width)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.requested_height)
                    cap.set(cv2.CAP_PROP_FPS, self.requested_fps)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                except Exception as exc:
                    logger.warning("Could not configure camera properties: %s", exc)

                self._cap = cap
                self.backend_name = label
                logger.info("Camera %d opened with %s: %s", self.camera_index, backend, self.get_properties())
                return self
            except CameraOpenError:
                raise
            except Exception as exc:  # pragma: no cover - fallback path
                last_error = str(exc)
                try:
                    self._release_device_lock()
                except Exception:
                    pass

        raise CameraOpenError(
            f"Unable to open camera at index {self.camera_index}. "
            "Possible causes: camera unavailable, in use by another app, "
            "wrong index, OS permission, or missing driver."
        )

    def is_opened(self) -> bool:
        return self._cap is not None and bool(self._cap.isOpened())

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        if not self.is_opened():
            return False, None
        assert self._cap is not None
        success, frame = self._cap.read()
        if not success or frame is None:
            return False, None
        return True, frame

    def release(self) -> None:
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception as exc:
                logger.warning("Error releasing camera: %s", exc)
            finally:
                self._cap = None
        self._release_device_lock()

    def get_properties(self) -> Dict[str, Any]:
        props: Dict[str, Any] = {
            "camera_index": self.camera_index,
            "width": self.requested_width,
            "height": self.requested_height,
            "fps": self.requested_fps,
            "backend": self.backend_name or self.backend.upper(),
        }
        if self._cap is not None:
            try:
                w = self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                h = self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                f = self._cap.get(cv2.CAP_PROP_FPS)
                if w and w > 0:
                    props["width"] = int(w)
                if h and h > 0:
                    props["height"] = int(h)
                if f and f > 0:
                    props["fps"] = float(f)
            except Exception as exc:
                logger.warning("Could not read camera properties: %s", exc)
        return props


def discover_cameras(
    indices: Iterable[int],
    backends: Iterable[str] = ("dshow", "msmf"),
    width: int = 640,
    height: int = 480,
) -> list[dict[str, Any]]:
    """Probe index/backend pairs one at a time and immediately release each device."""
    results: list[dict[str, Any]] = []
    for index_value in indices:
        index = int(index_value)
        if index < 0:
            raise ValueError("Camera indices must be zero or greater.")

        for backend in backends:
            normalized_backend = normalize_camera_backend(backend)
            cam = Camera(index, width=width, height=height, backend=normalized_backend)
            try:
                cam.open()
                if cam.is_opened():
                    props = cam.get_properties()
                    results.append(
                        {
                            "index": index,
                            "backend": normalized_backend,
                            "camera_index": index,
                            "width": props.get("width", width),
                            "height": props.get("height", height),
                            "fps": props.get("fps"),
                            "available": True,
                        }
                    )
                    cam.release()
                    break
            except CameraOpenError:
                pass
            finally:
                try:
                    cam.release()
                except Exception:
                    pass

    return results

