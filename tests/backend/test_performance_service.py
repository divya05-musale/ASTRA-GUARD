import time

from backend.services.performance_service import PerformanceMonitor


def test_monitor_calculates_delivery_metrics_and_resources():
    monitor = PerformanceMonitor()
    monitor.record_frame({
        "capture_fps": 24.0,
        "yolo_ms": 35.0,
        "mediapipe_ms": 14.0,
        "mission_event_ms": 8.0,
        "captured_monotonic": time.monotonic() - 0.05,
    })
    monitor.record_display(22.0, time.time())
    status = monitor.get_status()

    assert status["capture_fps"] == 24.0
    assert status["dashboard_display_fps"] == 22.0
    assert status["end_to_end_latency_ms"] >= 50.0
    assert status["end_to_end_display_latency_ms"] >= status["end_to_end_latency_ms"]
    assert status["system_ram_total_mb"] > 0
    assert "system_cpu_percent" in status
    assert "backend_process_ram_mb" in status