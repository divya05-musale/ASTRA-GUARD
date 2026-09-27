from pathlib import Path
import json

import cv2
import numpy as np
import pytest

from agent.perception.experiment_object_detector import ExperimentObjectDetector
from agent.perception.perception_event import PerceptionEvent
from backend.services.mission_service import MissionService
from backend.services.session_store import SessionStore
import backend.services.camera_service as camera_service


ROOT = Path(__file__).resolve().parents[2]


class SilentVoice:
    def speak_decision(self, **_kwargs):
        return False


class EmptyDetector:
    names = {}

    def detect(self, _frame):
        return []

    def draw_detections(self, frame, _detections):
        return frame.copy()


def _service(tmp_path, experiment_dir):
    service = MissionService(ROOT / "experiments" / experiment_dir)
    service._session_store = SessionStore(tmp_path / "records")
    service.session.voice_guidance = SilentVoice()
    return service


def _marker_frame(marker_id):
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker = cv2.aruco.generateImageMarker(dictionary, marker_id, 100)
    frame = np.full((300, 400, 3), 255, dtype=np.uint8)
    frame[80:180, 100:200] = cv2.cvtColor(marker, cv2.COLOR_GRAY2BGR)
    return frame


def test_plant_session_start_records_first_step_and_step_scoped_manual_permission(tmp_path):
    service = _service(tmp_path, "EXP007_PLANT_MONITORING")
    record = service.start_session()

    assert service.get_progress()["current_step"] == "S002"
    saved = service.get_session(record["session_id"])
    assert saved["events"][0]["decision_source"] == "session_start"
    assert saved["events"][0]["decision"]["step_id"] == "S001"
    assert service._manual_confirmation_allowed("S002") is True
    assert service._manual_confirmation_allowed("S003") is True
    assert service._manual_confirmation_allowed("S004") is False
    assert service._manual_confirmation_allowed("S006") is True
    assert service._manual_confirmation_allowed("S009") is True


def test_manual_plant_identification_requires_uncertain_observation_and_is_audited(tmp_path):
    service = _service(tmp_path, "EXP007_PLANT_MONITORING")
    record = service.start_session()
    uncertain = service.process_event(PerceptionEvent())
    assert uncertain["status"] == "UNCERTAIN"

    result = service.confirm_uncertain(record["session_id"], "plant-operator")
    saved = service.get_session(record["session_id"])

    assert result["decision_source"] == "manual_confirmation"
    assert result["manual_confirmation"]["operator"] == "plant-operator"
    assert saved["events"][-1]["manual_confirmation"]["source_uncertain_event"]
    assert service.get_progress()["current_step"] == "S003"


def test_manual_confirmation_is_rejected_for_non_opted_in_plant_step(tmp_path):
    service = _service(tmp_path, "EXP007_PLANT_MONITORING")
    record = service.start_session()
    service._session.adapter.engine.sm.advance()
    service._session.adapter.engine.sm.advance()
    assert service.get_progress()["current_step"] == "S004"

    with pytest.raises(ValueError, match="not enabled"):
        service.confirm_uncertain(record["session_id"], "plant-operator")


def test_plant_capture_and_report_actions_persist_local_files(tmp_path, monkeypatch):
    service = _service(tmp_path, "EXP007_PLANT_MONITORING")
    record = service.start_session()
    engine = service.session.adapter.engine
    for _ in range(5):
        step = engine.sm.current_step()
        result = engine.process({
            "activity": step["activity"],
            "object": step["expected_object"],
            "confidence": 1.0,
        })
        assert result["status"] == "CORRECT"
    assert service.get_progress()["current_step"] == "S007"
    class CameraStub:
        def get_jpeg(self):
            return b"\xff\xd8local-evidence\xff\xd9"

    monkeypatch.setattr(camera_service, "get_camera_service", lambda: CameraStub())
    service.perform_session_action(record["session_id"], "capture_evidence")
    saved = service.get_session(record["session_id"])
    image_evidence = next(item for item in saved["evidence"] if item["kind"] == "image")
    assert Path(image_evidence["path"]).read_bytes() == b"\xff\xd8local-evidence\xff\xd9"
    assert service.get_progress()["current_step"] == "S008"

    service.perform_session_action(record["session_id"], "save_observation")
    saved = service.get_session(record["session_id"])
    report = Path(saved["report_path"])
    assert report.is_file()
    assert json.loads(report.read_text(encoding="utf-8"))["experiment_id"] == "EXP007"
    assert service.get_progress()["current_step"] == "S009"


def test_payload_out_of_order_box_is_rejected_by_existing_decision_engine(tmp_path):
    service = _service(tmp_path, "EXP006_PAYLOAD_TRANSFER")
    record = service.start_session()
    detector = ExperimentObjectDetector(
        EmptyDetector(),
        ROOT / "experiments" / "EXP006_PAYLOAD_TRANSFER",
    )
    detector.set_frame_timestamp(20.0)
    detected_objects = detector.detect(_payload_boxes_in_zone_a())
    result = service.process_event(PerceptionEvent(objects=detected_objects))

    assert result["status"] == "DEVIATION"
    assert result["step_id"] == "S001"
    assert service.get_progress()["current_step"] == "S001"
    saved = service.get_session(record["session_id"])
    assert saved["events"][-1]["decision"]["status"] == "DEVIATION"


def _payload_boxes_in_zone_a():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.rectangle(frame, (60, 100), (180, 260), (0, 0, 255), -1)
    cv2.rectangle(frame, (380, 100), (500, 260), (0, 255, 255), -1)
    return frame
