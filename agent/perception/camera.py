"""Reusable OpenCV webcam capture layer for ASTRA-GUARD (Phase 5).

No object detection here. Frames stay in BGR. All processing is local.
"""
from __future__ import annotations

import logging
import os
import tempfile
import threading
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)
_CAMERA_LOCKS: set[str] = set()
_CAMERA_LOCKS_GUARD = threading.Lock()


class CameraOpenError(RuntimeError):
    """Raised when the webcam cannot be opened."""


class FrameReadError(RuntimeError):
    """Raised when a frame cannot be read from an opened camera."""


class Camera:
    """Thin reusable wrapper around cv2.VideoCapture."""

    def __init__(self, camera_index: int = 0, width: int = 1280,
                 height: int = 720, fps: int = 30) -> None:
        self.camera_index = int(camera_index)
        self.requested_width = int(width)
        self.requested_height = int(height)
        self.requested_fps = float(fps)
        self._cap: Optional[cv2.VideoCapture] = None
        self._device_lock = None
        self._device_lock_path = os.path.join(
            tempfile.gettempdir(),
            f"astra-guard-camera-{self.camera_index}.lock",
        )

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
        try:
            self._acquire_device_lock()
            cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        except Exception:
            self._release_device_lock()
            raise
        if cap is None or not cap.isOpened():
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass
            self._release_device_lock()
            raise CameraOpenError(
                f"Unable to open camera at index {self.camera_index}. "
                "Possible causes: camera unavailable, in use by another app, "
                "wrong index, OS permission, or missing driver."
            )
        try:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.requested_width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.requested_height)
            cap.set(cv2.CAP_PROP_FPS, self.requested_fps)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception as exc:
            logger.warning("Could not configure camera properties: %s", exc)
        self._cap = cap
        logger.info("Camera %d opened: %s", self.camera_index, self.get_properties())
        return self

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

