"""Publish only the newest annotated frame without blocking inference."""

from __future__ import annotations

import json
import threading
import time
import urllib.request

import cv2
import numpy as np


class LatestFramePublisher:
    """Encode and post frames on a worker with a one-frame pending slot."""

    def __init__(
        self,
        publish_url: str,
        quality: int = 75,
        timeout: float = 0.4,
    ) -> None:
        self.publish_url = str(publish_url)
        self.quality = int(quality)
        self.timeout = float(timeout)
        self._condition = threading.Condition()
        self._latest_frame: np.ndarray | None = None
        self._latest_metrics: dict[str, float] = {}
        self._latest_submitted_at = 0.0
        self._closed = False
        self.dropped_frames = 0
        self.sent_frames = 0
        self.failed_frames = 0
        self._last_publish_ms = 0.0
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="astra-live-frame-publisher",
        )
        self._thread.start()

    def submit(
        self,
        frame: np.ndarray,
        metrics: dict[str, float] | None = None,
    ) -> bool:
        """Replace any pending frame; callers must not mutate submitted frames."""

        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            return False

        with self._condition:
            if self._closed:
                return False
            if self._latest_frame is not None:
                self.dropped_frames += 1
            self._latest_frame = frame
            self._latest_metrics = dict(metrics or {})
            self._latest_submitted_at = time.monotonic()
            self._condition.notify()
        return True

    def _run(self) -> None:
        while True:
            with self._condition:
                self._condition.wait_for(
                    lambda: self._latest_frame is not None or self._closed
                )
                if self._latest_frame is None and self._closed:
                    return
                frame = self._latest_frame
                metrics = self._latest_metrics
                submitted_at = self._latest_submitted_at
                self._latest_frame = None

            try:
                encode_started = time.perf_counter()
                success, buffer = cv2.imencode(
                    ".jpg",
                    frame,
                    [int(cv2.IMWRITE_JPEG_QUALITY), self.quality],
                )
                if not success:
                    raise RuntimeError("Could not encode camera frame")

                metrics.update({
                    "jpeg_encode_ms": round((time.perf_counter() - encode_started) * 1000.0, 2),
                    "frame_publish_ms": round(self._last_publish_ms, 2),
                    "publisher_queue_ms": round(max(0.0, time.monotonic() - submitted_at) * 1000.0, 2),
                    "publisher_dropped_frames": float(self.dropped_frames),
                })

                request = urllib.request.Request(
                    self.publish_url,
                    data=buffer.tobytes(),
                    headers={
                        "Content-Type": "image/jpeg",
                        "X-Frame-Width": str(frame.shape[1]),
                        "X-Frame-Height": str(frame.shape[0]),
                        "X-Performance-Metrics": json.dumps(metrics, separators=(",", ":")),
                    },
                    method="POST",
                )
                publish_started = time.perf_counter()
                with urllib.request.urlopen(
                    request,
                    timeout=self.timeout,
                ) as response:
                    response.read(1)
                with self._condition:
                    self.sent_frames += 1
                    self._last_publish_ms = (time.perf_counter() - publish_started) * 1000.0
            except Exception:
                with self._condition:
                    self.failed_frames += 1

    def close(self) -> None:
        with self._condition:
            self._closed = True
            self._condition.notify_all()
        self._thread.join(timeout=self.timeout * 2 + 0.5)