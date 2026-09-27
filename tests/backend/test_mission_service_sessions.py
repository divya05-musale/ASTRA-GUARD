from agent.perception.perception_event import PerceptionEvent
from backend.services.mission_service import MissionService
from backend.services.session_store import SessionStore


class SilentVoice:
    def speak_decision(self, **_kwargs):
        return False


def _service(tmp_path):
    service = MissionService()
    service._session_store = SessionStore(tmp_path)
    service.session.voice_guidance = SilentVoice()
    return service


def test_closed_session_does_not_auto_start_again(tmp_path):
    service = _service(tmp_path)
    record = service.start_session()
    service.end_session("CANCELLED")

    result = service.process_event(PerceptionEvent())

    assert result["status"] == "SESSION_CLOSED"
    assert service.active_session_id == record["session_id"]
    assert service.list_sessions()[0]["session_id"] == record["session_id"]


def test_camera_event_cannot_be_mixed_into_video_session(tmp_path):
    service = _service(tmp_path)
    record = service.start_session(input_source="video")

    result = service.process_event(PerceptionEvent(source="camera"))

    assert result["status"] == "SESSION_SOURCE_MISMATCH"
    assert service.get_session(record["session_id"])["events"] == []


def test_manual_confirmation_is_recorded_as_a_separate_decision(tmp_path):
    service = _service(tmp_path)
    record = service.start_session()
    service._session_store.append_event(record["session_id"], {
        "timestamp": "2026-09-27T00:00:00+00:00",
        "decision_source": "automatic",
        "decision": {"status": "UNCERTAIN", "step_id": "S001"},
        "perception": {"confidence": 0.2},
    })

    result = service.confirm_uncertain(record["session_id"], "operator-test")
    saved = service.get_session(record["session_id"])

    assert result["status"] == "CORRECT"
    assert result["decision_source"] == "manual_confirmation"
    assert result["perception"]["source"] == "manual"
    assert saved["events"][0]["decision_source"] == "automatic"
    assert saved["events"][1]["manual_confirmation"]["operator"] == "operator-test"
    assert service.get_progress()["current_step"] == "S002"


def test_identical_deviations_are_persisted_as_one_aggregate(tmp_path):
    service = _service(tmp_path)
    record = service.start_session()
    timestamp = 0

    def repeated_deviation(_event):
        nonlocal timestamp
        timestamp += 1
        return {
            "status": "DEVIATION",
            "step_id": "S001",
            "deviation_type": "WRONG_OBJECT",
            "detected_activity": "CHECK_EQUIPMENT",
            "detected_object": "experiment_controller",
            "expected_object": "experiment_container",
            "guidance": "Use the expected equipment.",
            "perception": {"timestamp": str(timestamp)},
        }

    service.session.process_event = repeated_deviation
    for _ in range(12):
        service.process_event(PerceptionEvent())
    service.end_session("CANCELLED")

    saved = service.get_session(record["session_id"])
    assert len(saved["events"]) == 1
    assert saved["events"][0]["repeat_count"] == 12
