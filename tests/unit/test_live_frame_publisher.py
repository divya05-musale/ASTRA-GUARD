import threading

import cv2
import json
import time
import numpy as np

from agent.perception import live_frame_publisher
from agent.perception.live_frame_publisher import LatestFramePublisher


def test_publisher_transmits_stage_metrics(monkeypatch):
    completed = threading.Event()
    received = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, _size):
            return b"ok"

    def fake_urlopen(request, timeout):
        received.update(json.loads(request.get_header("X-performance-metrics")))
        completed.set()
        return Response()

    monkeypatch.setattr(live_frame_publisher.urllib.request, "urlopen", fake_urlopen)
    publisher = LatestFramePublisher("http://127.0.0.1/api/camera/publish")
    try:
        assert publisher.submit(
            np.zeros((8, 8, 3), dtype=np.uint8),
            metrics={
                "capture_fps": 24.0,
                "yolo_ms": 35.0,
                "captured_monotonic": 1234.5,
            },
        )
        assert completed.wait(timeout=2.0)
    finally:
        publisher.close()

    assert received["capture_fps"] == 24.0
    assert received["yolo_ms"] == 35.0
    assert received["captured_monotonic"] == 1234.5
    assert received["jpeg_encode_ms"] >= 0.0


def test_publisher_replaces_stale_pending_frame(monkeypatch):
    request_started = threading.Event()
    allow_request = threading.Event()
    received_values = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, size):
            return b"{"

    def fake_urlopen(request, timeout):
        image = cv2.imdecode(
            np.frombuffer(request.data, dtype=np.uint8),
            cv2.IMREAD_COLOR,
        )
        received_values.append(int(image[0, 0, 0]))
        if len(received_values) == 1:
            request_started.set()
            allow_request.wait(timeout=2.0)
        return Response()

    monkeypatch.setattr(live_frame_publisher.urllib.request, "urlopen", fake_urlopen)
    publisher = LatestFramePublisher("http://example.test/camera/publish")
    try:
        assert publisher.submit(np.full((8, 8, 3), 10, dtype=np.uint8))
        assert request_started.wait(timeout=1.0)
        assert publisher.submit(np.full((8, 8, 3), 20, dtype=np.uint8))
        assert publisher.submit(np.full((8, 8, 3), 30, dtype=np.uint8))
    finally:
        allow_request.set()
        publisher.close()

    assert received_values == [10, 30]
    assert publisher.dropped_frames == 1
    assert publisher.sent_frames == 2
