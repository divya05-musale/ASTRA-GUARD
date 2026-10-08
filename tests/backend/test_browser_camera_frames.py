from __future__ import annotations

import threading

import numpy as np
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
            "detected_object": event.objects[0]["name"],
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


def test_browser_frame_endpoint_accepts_upload_without_opening_camera(monkeypatch):
    camera = _FakeCameraPublisher()
    monkeypatch.setattr("backend.api.camera.get_camera_service", lambda: camera)
    monkeypatch.setattr(
        "backend.api.camera.get_browser_perception_service",
        lambda: type("Processor", (), {
            "process_frame": lambda _self, frame: {
                "event": {"source": "camera", "objects": [], "hands": []},
                "result": {"status": "UNCERTAIN", "step_id": "S001"},
                "timings_ms": {"yolo_ms": 4.0, "mediapipe_ms": 3.0},
                "frames_processed": 1,
            },
        })(),
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
    assert response.json()["result"]["status"] == "UNCERTAIN"
    assert len(camera.frames) == 1
    assert camera.frames[0][1]["camera_source"] == "laptop"


def test_browser_frame_endpoint_rejects_invalid_jpeg():
    response = client.post(
        "/api/camera/browser-frame",
        content=b"not a jpeg",
        headers={"Content-Type": "image/jpeg"},
    )

    assert response.status_code == 400


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