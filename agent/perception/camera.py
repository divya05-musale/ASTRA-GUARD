"""Reusable OpenCV webcam capture layer for ASTRA-GUARD (Phase 5).

No object detection here. Frames stay in BGR. All processing is local.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


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

    def open(self) -> "Camera":
        cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if cap is None or not cap.isOpened():
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass
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

