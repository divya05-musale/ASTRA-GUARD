"""Frame-preserving compatibility renderer for the live perception pipeline."""

from __future__ import annotations

from typing import Any, Dict

import numpy as np


class LiveOverlay:
    """Preserve the annotated video frame without adding a text HUD."""

    @staticmethod
    def _safe_text(
        value: Any,
        default: str = "UNKNOWN",
    ) -> str:
        """Convert a value to display-safe text."""

        if value is None:
            return default

        text = str(value).strip()

        if not text:
            return default

        return text

    @staticmethod
    def _safe_confidence(
        value: Any,
    ) -> float:
        """Convert confidence to a value between 0 and 1."""

        try:
            confidence = float(value)
        except (TypeError, ValueError):
            return 0.0

        return max(
            0.0,
            min(1.0, confidence),
        )

    @staticmethod
    def _safe_progress(
        progress: Any,
    ) -> float:
        """Convert mission progress to a value between 0 and 100."""

        try:
            value = float(progress)
        except (TypeError, ValueError):
            return 0.0

        return max(
            0.0,
            min(100.0, value),
        )

    def draw(
        self,
        frame: np.ndarray,
        result: Dict[str, Any],
        mission_status: Dict[str, Any] | None = None,
    ) -> np.ndarray:
        """
        Keep the existing renderer interface while leaving the frame unchanged.

        Parameters
        ----------
        frame:
            OpenCV BGR video frame.

        result:
            Current protocol decision result.

        mission_status:
            Dashboard-ready mission status returned by MissionStatus.
        """

        if frame is None:
            raise ValueError(
                "frame cannot be None"
            )

        if (
            not isinstance(frame, np.ndarray)
            or frame.ndim != 3
            or frame.shape[2] != 3
        ):
            raise ValueError(
                "frame must be an OpenCV BGR image"
            )

        if not isinstance(result, dict):
            raise TypeError(
                "result must be a dictionary"
            )

        if mission_status is not None and not isinstance(
            mission_status,
            dict,
        ):
            raise TypeError(
                "mission_status must be a dictionary or None"
            )

        return frame.copy()