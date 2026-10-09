from __future__ import annotations

import threading
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from agent.perception.perception_event import PerceptionEvent
from backend.core.config import Settings
from backend.main import app
from backend.services import browser_perception_service as browser_service_module
from backend.services import camera_service as camera_service_module
from backend.services.browser_perception_service import BrowserPerceptionService
from backend.services.camera_service import CameraService, encode_bgr_to_jpeg


client = TestClient(app)


class _FakeMissionService:
    _protocol_path = "experiments/EXP001_TARDIGRADE"

    def get_protocol(self):
        return {"experiment": {"experiment_id": "EXP001"}}

    def get_status(self):
        return {"status": "IDLE"}

    def process_event(self, event):
        return {
            "status": "CORRECT",
            "step_id": "S001",
            "next_step_id": "S002",
            "detected_object": event.objects[0].get("name", event.objects[0].get("class_name")) if event.objects else None,
            "perception": {"activity": "CHECK_EQUIPMENT", "confidence": 0.91},
        }


class _FakeDetector:
    def __init__(self, **_kwargs):
        pass

    def detect(self, _frame):
        return [{"name": "experiment_container", "confidence": 0.91}]


class _FakeExperimentDetector:
    def __init__(self, base_detector, _path, protocol_client=None):
        self.base_detector = base_detector

    def detect(self, frame):
        return self.base_detector.detect(frame)

    def apply_hand_context(self, _objects, _hands, _shape):
        pass


class _FakeHandTracker:
    def __init__(self):
        pass

    def process(self, _frame):
        return [{"confidence": 0.95, "center": [20, 20], "landmarks": []}]


class _FakeCameraPublisher:
    def __init__(self):
        self.frames = []

    def publish_external_jpeg(self, jpeg, **metadata):
        self.frames.append((jpeg, metadata))
        return True


def _jpeg_frame():
    jpeg = encode_bgr_to_jpeg(np.full((48, 64, 3), 120, dtype=np.uint8))
    assert jpeg is not None
    return jpeg


def test_browser_frame_runs_existing_processor_and_mission_service(monkeypatch):
    mission = _FakeMissionService()
    monkeypatch.setattr(browser_service_module, "get_settings", lambda: Settings())
    monkeypatch.setattr(browser_service_module, "get_mission_service", lambda: mission)
    monkeypatch.setattr(browser_service_module, "ObjectDetector", _FakeDetector)
    monkeypatch.setattr(browser_service_module, "ExperimentObjectDetector", _FakeExperimentDetector)
    monkeypatch.setattr(browser_service_module, "HandTracker", _FakeHandTracker)
    monkeypatch.setattr(
        browser_service_module,
        "get_performance_monitor",
        lambda: type("Monitor", (), {"record_frame": lambda _self, _metrics: None})(),
    )

    service = BrowserPerceptionService()
    processed = service.process_frame(np.full((48, 64, 3), 120, dtype=np.uint8))

    assert processed["event"]["source"] == "camera"
    assert processed["event"]["objects"][0]["name"] == "experiment_container"
    assert processed["result"]["status"] == "CORRECT"
    assert processed["frames_processed"] == 1
    status = service.get_status()
    assert status["inference_active"] is True
    assert status["last_object_count"] == 1
    assert status["last_hand_count"] == 1
    assert status["latest_objects"] == processed["event"]["objects"]
    assert status["latest_hands"] == processed["event"]["hands"]
    assert status["yolo_status"] == "ONLINE"
    assert status["mediapipe_status"] == "ONLINE"


def test_browser_frame_keeps_yolo_online_when_mediapipe_initialization_fails(monkeypatch):
    mission = _FakeMissionService()
    monkeypatch.setattr(browser_service_module, "get_settings", lambda: Settings())
    monkeypatch.setattr(browser_service_module, "get_mission_service", lambda: mission)
    monkeypatch.setattr(browser_service_module, "ObjectDetector", _FakeDetector)
    monkeypatch.setattr(browser_service_module, "ExperimentObjectDetector", _FakeExperimentDetector)

    def fail_hand_tracker():
        raise RuntimeError("MediaPipe HandLandmarker initialization failed: missing GLES")

    monkeypatch.setattr(browser_service_module, "HandTracker", fail_hand_tracker)
    monkeypatch.setattr(
        browser_service_module,
        "get_performance_monitor",
        lambda: type("Monitor", (), {"record_frame": lambda _self, _metrics: None})(),
    )

    service = BrowserPerceptionService()
    processed = service.process_frame(np.full((48, 64, 3), 120, dtype=np.uint8))

    assert processed["event"]["objects"] == [{"name": "experiment_container", "confidence": 0.91}]
    assert processed["event"]["hands"] == []
    assert processed["result"]["status"] == "CORRECT"
    status = service.get_status()
    assert status["processor_status"] == "READY"
    assert status["yolo_status"] == "ONLINE"
    assert status["mediapipe_status"] == "UNAVAILABLE"
    assert "missing GLES" in status["mediapipe_error"]
    assert status["error"] is None


def test_browser_frame_endpoint_accepts_upload_without_opening_camera(monkeypatch):
    camera = _FakeCameraPublisher()
    accepted_frames = []

    class _Queue:
        def enqueue_frame(self, frame):
            accepted_frames.append(frame.copy())
            return {
                "frame_id": 1,
                "frames_received": 1,
                "frames_accepted": 1,
                "frames_processed": 0,
                "queue_depth": 1,
            }

    monkeypatch.setattr("backend.api.camera.get_camera_service", lambda: camera)
    monkeypatch.setattr(
        "backend.api.camera.get_browser_perception_service",
        lambda: _Queue(),
    )
    monkeypatch.setattr(
        "backend.api.camera.cv2.VideoCapture",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("cloud must not open cameras")),
    )

    response = client.post(
        "/api/camera/browser-frame",
        content=_jpeg_frame(),
        headers={"Content-Type": "image/jpeg"},
    )

    assert response.status_code == 200
    assert response.json()["accepted"] is True
    assert response.json()["event"] is None
    assert response.json()["result"] is None
    assert response.json()["timings_ms"] is None
    assert response.json()["frames_processed"] == 0
    assert response.json()["frame_id"] == 1
    assert accepted_frames[0].shape == (48, 64, 3)
    assert len(camera.frames) == 1
    assert camera.frames[0][1]["camera_source"] == "laptop"


def test_browser_frame_endpoint_rejects_invalid_jpeg():
    response = client.post(
        "/api/camera/browser-frame",
        content=b"not a jpeg",
        headers={"Content-Type": "image/jpeg"},
    )

    assert response.status_code == 400


def test_browser_frame_endpoint_rejects_empty_upload():
    response = client.post(
        "/api/camera/browser-frame",
        content=b"",
        headers={"Content-Type": "image/jpeg"},
    )

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_browser_frame_endpoint_rejects_jpeg_markers_with_invalid_image_data(monkeypatch):
    monkeypatch.setattr("backend.api.camera.get_camera_service", lambda: _FakeCameraPublisher())

    response = client.post(
        "/api/camera/browser-frame",
        content=b"\xff\xd8not-an-image\xff\xd9",
        headers={"Content-Type": "image/jpeg"},
    )

    assert response.status_code == 400
    assert "decode" in response.json()["detail"].lower()


def test_browser_frame_endpoint_reports_queue_backpressure(monkeypatch):
    monkeypatch.setattr("backend.api.camera.get_camera_service", lambda: _FakeCameraPublisher())

    class _FullQueue:
        def enqueue_frame(self, _frame):
            raise browser_service_module.FrameQueueFullError("full")

    monkeypatch.setattr("backend.api.camera.get_browser_perception_service", lambda: _FullQueue())
    response = client.post(
        "/api/camera/browser-frame",
        content=_jpeg_frame(),
        headers={"Content-Type": "image/jpeg"},
    )

    assert response.status_code == 429
    assert response.headers["retry-after"] == "1"
    assert "queue is full" in response.json()["detail"]


def test_browser_frame_endpoint_acknowledges_while_inference_is_still_running(monkeypatch):
    started = threading.Event()
    release = threading.Event()

    class _BlockingProcessor:
        def process_frame(self, _frame, source):
            assert source == "camera"
            started.set()
            assert release.wait(timeout=3)
            return {
                "event": PerceptionEvent(),
                "result": {"status": "UNCERTAIN"},
                "timings_ms": {"yolo_ms": 1.0},
            }

    monkeypatch.setattr("backend.api.camera.get_camera_service", lambda: _FakeCameraPublisher())
    monkeypatch.setattr(browser_service_module, "get_mission_service", lambda: _FakeMissionService())
    monkeypatch.setattr(
        browser_service_module,
        "get_performance_monitor",
        lambda: type("Monitor", (), {"record_frame": lambda _self, _metrics: None})(),
    )
    service = BrowserPerceptionService()
    service._processor = _BlockingProcessor()
    monkeypatch.setattr("backend.api.camera.get_browser_perception_service", lambda: service)

    try:
        response = client.post(
            "/api/camera/browser-frame",
            content=_jpeg_frame(),
            headers={"Content-Type": "image/jpeg"},
        )

        assert response.status_code == 200
        assert response.json()["accepted"] is True
        assert started.wait(timeout=1)
        status = service.get_status()
        assert status["processing"] is True
        assert status["frames_processed"] == 0
        assert status["frames_accepted"] == 1
    finally:
        release.set()
        service._frame_queue.join()


def test_browser_frame_queue_is_bounded_under_repeated_uploads(monkeypatch):
    started = threading.Event()
    release = threading.Event()

    class _BlockingProcessor:
        def process_frame(self, _frame, source):
            assert source == "camera"
            started.set()
            assert release.wait(timeout=3)
            return {
                "event": PerceptionEvent(),
                "result": {"status": "UNCERTAIN"},
                "timings_ms": {},
            }

    monkeypatch.setattr(browser_service_module, "get_mission_service", lambda: _FakeMissionService())
    monkeypatch.setattr(
        browser_service_module,
        "get_performance_monitor",
        lambda: type("Monitor", (), {"record_frame": lambda _self, _metrics: None})(),
    )
    service = BrowserPerceptionService()
    service._processor = _BlockingProcessor()
    frame = np.full((48, 64, 3), 120, dtype=np.uint8)

    try:
        first = service.enqueue_frame(frame)
        assert started.wait(timeout=1)
        second = service.enqueue_frame(frame)
        with pytest.raises(browser_service_module.FrameQueueFullError):
            service.enqueue_frame(frame)

        status = service.get_status()
        assert first["frame_id"] != second["frame_id"]
        assert status["frames_received"] == 3
        assert status["frames_accepted"] == 2
        assert status["frames_rejected"] == 1
        assert status["queue_depth"] <= 1
        assert status["frames_processed"] == 0
    finally:
        release.set()
        service._frame_queue.join()

    assert service.get_status()["frames_processed"] == 2


def test_browser_worker_reports_inference_failures(monkeypatch):
    finished = threading.Event()

    class _FailingProcessor:
        def process_frame(self, _frame, source):
            assert source == "camera"
            finished.set()
            raise RuntimeError("YOLO inference failed: test failure")

    monkeypatch.setattr(browser_service_module, "get_mission_service", lambda: _FakeMissionService())
    service = BrowserPerceptionService()
    service._processor = _FailingProcessor()
    service.enqueue_frame(np.full((48, 64, 3), 120, dtype=np.uint8))

    assert finished.wait(timeout=1)
    service._frame_queue.join()
    status = service.get_status()

    assert status["frames_failed"] == 1
    assert status["frames_processed"] == 0
    assert status["error"] == "YOLO inference failed: test failure"
    assert status["latest_objects"] == []
    assert status["detections_fresh"] is False


def test_status_has_no_detection_until_inference_completes(monkeypatch):
    monkeypatch.setattr(browser_service_module, "get_mission_service", lambda: _FakeMissionService())
    status = BrowserPerceptionService().get_status()

    assert status["frames_processed"] == 0
    assert status["latest_objects"] == []
    assert status["latest_event"] is None
    assert status["detections_fresh"] is False


def test_browser_frame_runs_real_yolo_on_bundled_image(monkeypatch):
    ultralytics = pytest.importorskip("ultralytics")
    image_path = Path(ultralytics.__file__).parent / "assets" / "bus.jpg"
    model_path = Path("yolo11n.pt")
    if not image_path.is_file() or not model_path.is_file():
        pytest.skip("Bundled Ultralytics image or configured local YOLO weights are unavailable.")

    frame = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    assert frame is not None and frame.size > 0
    mission = _FakeMissionService()
    monkeypatch.setattr(
        browser_service_module,
        "get_settings",
        lambda: Settings(ENABLE_MEDIAPIPE=False),
    )
    monkeypatch.setattr(browser_service_module, "get_mission_service", lambda: mission)
    monkeypatch.setattr(
        browser_service_module,
        "get_performance_monitor",
        lambda: type("Monitor", (), {"record_frame": lambda _self, _metrics: None})(),
    )
    service = BrowserPerceptionService()
    monkeypatch.setattr("backend.api.camera.get_camera_service", lambda: _FakeCameraPublisher())
    monkeypatch.setattr("backend.api.camera.get_browser_perception_service", lambda: service)

    jpeg = encode_bgr_to_jpeg(frame)
    assert jpeg is not None
    response = client.post(
        "/api/camera/browser-frame",
        content=jpeg,
        headers={"Content-Type": "image/jpeg"},
    )
    assert response.status_code == 200
    assert response.json()["accepted"] is True
    service._frame_queue.join()
    status = service.get_status()

    assert status["frames_received"] == 1
    assert status["frames_accepted"] == 1
    assert status["frames_processed"] == 1
    assert status["latest_event"]["objects"]
    assert all(item.get("class_name") and item.get("bbox") for item in status["latest_objects"])
    assert status["latest_timings_ms"]["yolo_ms"] > 0


def test_perception_status_endpoint_reports_pipeline_fields():
    response = client.get("/api/perception/status")

    assert response.status_code == 200
    body = response.json()
    assert "inference_active" in body
    assert "yolo_status" in body
    assert "mediapipe_status" in body
    assert "processor_status" in body
    assert "mission_engine_status" in body
    assert "last_object_count" in body
    assert "last_hand_count" in body


def test_perception_status_reports_model_initialization_failure(monkeypatch):
    monkeypatch.setattr(
        browser_service_module,
        "get_mission_service",
        lambda: _FakeMissionService(),
    )
    service = BrowserPerceptionService()
    service._initialization_error = "YOLO model unavailable"

    status = service.get_status()

    assert status["processor_status"] == "ERROR"
    assert status["yolo_status"] == "ERROR"
    assert status["mediapipe_status"] == "ERROR"


def test_perception_status_remains_responsive_during_frame_processing(monkeypatch):
    started = threading.Event()
    release = threading.Event()

    class _BlockingProcessor:
        def process_frame(self, _frame, source):
            assert source == "camera"
            started.set()
            assert release.wait(timeout=2)
            return {
                "event": PerceptionEvent(),
                "result": {"status": "UNCERTAIN"},
                "timings_ms": {},
            }

    monkeypatch.setattr(
        browser_service_module,
        "get_mission_service",
        lambda: _FakeMissionService(),
    )
    monkeypatch.setattr(
        browser_service_module,
        "get_performance_monitor",
        lambda: type("Monitor", (), {"record_frame": lambda _self, _metrics: None})(),
    )
    service = BrowserPerceptionService()
    service._processor = _BlockingProcessor()
    worker = threading.Thread(
        target=service.process_frame,
        args=(np.full((48, 64, 3), 120, dtype=np.uint8),),
    )

    worker.start()
    try:
        assert started.wait(timeout=1)
        status = service.get_status()
        assert status["processing"] is True
        assert status["processor_status"] == "PROCESSING"
        assert status["mission_engine_status"] == "ONLINE"
    finally:
        release.set()
        worker.join(timeout=2)
    assert not worker.is_alive()


def test_cloud_camera_status_reports_uploaded_frames_without_opening_device(monkeypatch):
    monkeypatch.setattr(camera_service_module, "get_settings", lambda: Settings(MODE="cloud"))
    service = CameraService()
    assert service.publish_external_jpeg(
        _jpeg_frame(),
        width=64,
        height=48,
        camera_source="laptop",
        camera_source_name="Browser Webcam",
    )

    status = service.get_status()

    assert status["connected"] is True
    assert status["has_frame"] is True
    assert status["frames_captured"] == 1
    assert status["camera_open"] is False
    assert status["capture_running"] is False
    assert status["cloud_mode"] is True