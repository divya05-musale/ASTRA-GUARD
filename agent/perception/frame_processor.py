"""Lightweight OpenCV frame utilities (Phase 5). No object detection."""
from __future__ import annotations

from typing import Any, Dict, Optional

import cv2
import numpy as np


class FrameProcessor:
    """Basic resize / grayscale / info helpers. Frames stay BGR unless converted."""

    def resize(self, frame: np.ndarray, width: Optional[int] = None,
               height: Optional[int] = None) -> np.ndarray:
        if frame is None:
            raise ValueError("resize received None frame")
        if width is None and height is None:
            raise ValueError("resize requires width and/or height")
        h, w = frame.shape[:2]
        if width is not None and width <= 0:
            raise ValueError("resize width must be positive")
        if height is not None and height <= 0:
            raise ValueError("resize height must be positive")
        if width is not None and height is not None:
            # Explicit W+H: honor exact request (documented stretch behavior).
            return cv2.resize(frame, (int(width), int(height)))
        if width is not None:
            scale = float(width) / float(w)
            return cv2.resize(frame, (int(width), max(1, int(round(h * scale)))))
        scale = float(height) / float(h)  # type: ignore[arg-type]
        return cv2.resize(frame, (max(1, int(round(w * scale))), int(height)))

    def convert_to_gray(self, frame: np.ndarray) -> np.ndarray:
        if frame is None:
            raise ValueError("convert_to_gray received None frame")
        if len(frame.shape) == 2:
            return frame
        if len(frame.shape) != 3 or frame.shape[2] != 3:
            raise ValueError("convert_to_gray expects a BGR frame")
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    def calculate_frame_info(self, frame: np.ndarray) -> Dict[str, Any]:
        if frame is None:
            raise ValueError("calculate_frame_info received None frame")
        h, w = frame.shape[:2]
        channels = 1 if len(frame.shape) == 2 else int(frame.shape[2])
        return {"width": int(w), "height": int(h),
                "channels": channels, "dtype": str(frame.dtype)}

