"""In-memory live performance telemetry for the local pipeline."""

from __future__ import annotations

import threading
import time
from typing import Any, Dict

import psutil


class PerformanceMonitor:
    """Collect latest-frame stage timings without retaining frame history."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._latest: Dict[str, Any] = {}
        self._last_frame_monotonic: float | None = None
        self._process = psutil.Process()

    def record_frame(self, metrics: Dict[str, Any]) -> None:
        now_monotonic = time.monotonic()
        now_wall = time.time()
        with self._lock:
            previous = self._last_frame_monotonic
            self._last_frame_monotonic = now_monotonic
            if previous is not None and now_monotonic > previous:
                self._latest["backend_stream_fps"] = round(
                    1.0 / (now_monotonic - previous), 2
                )
            for key in (
                "capture_fps", "yolo_ms", "mediapipe_ms", "mission_event_ms",
                "process_frame_ms", "jpeg_encode_ms", "frame_publish_ms", "publisher_queue_ms",
                "publisher_dropped_frames", "captured_monotonic",
            ):
                if key in metrics:
                    self._latest[key] = metrics[key]
            captured = metrics.get("captured_monotonic")
            try:
                latency = (now_monotonic - float(captured)) * 1000.0
            except (TypeError, ValueError):
                latency = None
            self._latest["end_to_end_latency_ms"] = (
                round(max(0.0, latency), 2) if latency is not None else None
            )
            self._latest["frame_received_at"] = now_wall
            self._latest["metrics_updated_at"] = now_wall

    def record_display(self, displayed_fps: float, displayed_at: float) -> None:
        with self._lock:
            self._latest["dashboard_display_fps"] = round(max(0.0, float(displayed_fps)), 2)
            self._latest["dashboard_displayed_at"] = float(displayed_at)
            received = self._latest.get("frame_received_at")
            self._latest["display_latency_ms"] = (
                round(max(0.0, (float(displayed_at) - received) * 1000.0), 2)
                if received is not None
                else None
            )
            capture_delay = self._latest.get("end_to_end_latency_ms")
            render_delay = self._latest.get("display_latency_ms")
            self._latest["end_to_end_display_latency_ms"] = (
                round(capture_delay + render_delay, 2)
                if capture_delay is not None and render_delay is not None
                else None
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            result = dict(self._latest)
        memory = psutil.virtual_memory()
        result.update({
            "system_cpu_percent": psutil.cpu_percent(interval=None),
            "system_ram_used_mb": round(memory.used / (1024 * 1024), 1),
            "system_ram_total_mb": round(memory.total / (1024 * 1024), 1),
            "backend_process_cpu_percent": self._process.cpu_percent(interval=None),
            "backend_process_ram_mb": round(self._process.memory_info().rss / (1024 * 1024), 1),
        })
        return result


_monitor: PerformanceMonitor | None = None
_monitor_lock = threading.Lock()


def get_performance_monitor() -> PerformanceMonitor:
    global _monitor
    if _monitor is None:
        with _monitor_lock:
            if _monitor is None:
                _monitor = PerformanceMonitor()
    return _monitor