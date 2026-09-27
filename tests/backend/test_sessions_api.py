from fastapi.testclient import TestClient

from backend.main import app
from backend.services.session_store import SessionStore
import backend.api.sessions as sessions_api


client = TestClient(app)


class FakeMissionService:
    def __init__(self, directory):
        self._session_store = SessionStore(directory)
        self.active_session_id = None

    def start_session(self, input_source, evidence_path):
        record = self._session_store.create({
            "experiment_id": "EXP001",
            "experiment_name": "Local test protocol",
            "input_source": input_source,
            "evidence": [{"path": evidence_path, "kind": "video"}],
        })
        self.active_session_id = record["session_id"]
        return record

    def get_session(self, session_id):
        return self._session_store.get(session_id)

    def get_progress(self):
        return {"current_step": "S001"}


def test_local_video_upload_is_saved_and_playable(monkeypatch, tmp_path):
    mission = FakeMissionService(tmp_path / "sessions")
    video_root = tmp_path / "videos"
    scheduled = []
    monkeypatch.setattr(sessions_api, "VIDEO_ROOT", video_root)
    monkeypatch.setattr(sessions_api, "find_valid_experiment", lambda _id: tmp_path)
    monkeypatch.setattr(sessions_api, "get_mission_service", lambda: mission)
    monkeypatch.setattr(sessions_api, "reset_mission_service", lambda _path: mission)
    monkeypatch.setattr(sessions_api, "reset_protocol_service", lambda _path: None)
    monkeypatch.setattr(
        sessions_api,
        "process_video_session",
        lambda session_id, path: scheduled.append((session_id, path)),
    )

    response = client.post(
        "/api/sessions/video/start?experiment_id=EXP001&filename=sample.mp4",
        content=b"local video bytes",
        headers={"Content-Type": "application/octet-stream"},
    )

    assert response.status_code == 200
    record = response.json()["session"]
    evidence_path = record["evidence"][0]["path"]
    assert record["input_source"] == "video"
    assert open(evidence_path, "rb").read() == b"local video bytes"
    assert scheduled == [(record["session_id"], evidence_path)]

    playback = client.get(f"/api/sessions/{record['session_id']}/video")
    assert playback.status_code == 200
    assert playback.content == b"local video bytes"

    mission._session_store.append_event(record["session_id"], {
        "timestamp": "2026-09-27T00:00:00+00:00",
        "decision_source": "manual_confirmation",
        "manual_confirmation": {"operator": "operator-test"},
        "perception": {"activity": "CHECK_EQUIPMENT", "object": "experiment_container"},
        "decision": {"step_id": "S001", "status": "CORRECT"},
    })
    json_export = client.get(f"/api/sessions/{record['session_id']}/export?format=json")
    assert json_export.status_code == 200
    assert json_export.json()["events"][0]["decision_source"] == "manual_confirmation"
    csv_export = client.get(f"/api/sessions/{record['session_id']}/export?format=csv")
    assert csv_export.status_code == 200
    assert "manual_confirmation" in csv_export.text
    assert "operator-test" in csv_export.text
    assert "evidence_captured" in csv_export.text
    assert "EXP001" in csv_export.text


def test_video_upload_rejects_unsupported_extension():
    response = client.post(
        "/api/sessions/video/start?experiment_id=EXP001&filename=notes.txt",
        content=b"not video",
        headers={"Content-Type": "application/octet-stream"},
    )
    assert response.status_code == 415


def test_configured_session_action_api(monkeypatch):
    class Mission:
        def perform_session_action(self, session_id, action, operator):
            return {
                "session_id": session_id,
                "action": action,
                "operator": operator,
            }

    monkeypatch.setattr(sessions_api, "get_mission_service", lambda: Mission())
    response = client.post(
        "/api/sessions/session-id/actions",
        json={"action": "capture_evidence", "operator": "local-operator"},
    )

    assert response.status_code == 200
    assert response.json()["action"] == "capture_evidence"
    assert response.json()["operator"] == "local-operator"


def test_saved_image_evidence_is_served_from_local_session_path(monkeypatch, tmp_path):
    mission = FakeMissionService(tmp_path / "sessions")
    evidence_root = tmp_path / "execution"
    monkeypatch.setattr(sessions_api, "EVIDENCE_ROOT", evidence_root)
    monkeypatch.setattr(sessions_api, "get_mission_service", lambda: mission)
    image_path = evidence_root / "evidence" / "session" / "S007.jpg"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"local-jpeg-evidence")
    record = mission._session_store.create({
        "experiment_id": "EXP007",
        "input_source": "webcam",
        "evidence": [{"kind": "image", "path": str(image_path)}],
    })

    response = client.get(f"/api/sessions/{record['session_id']}/evidence/S007.jpg")
    assert response.status_code == 200
    assert response.content == b"local-jpeg-evidence"
    assert client.get(f"/api/sessions/{record['session_id']}/evidence/../outside.jpg").status_code == 404
