"""POST /api/mission/event — real perception → mission-state bridge tests.

Uses the shared singleton from get_mission_service() so POST and GET
endpoints operate on the SAME mission session. No duplicated decision
logic and no fake events: values asserted here must come from the
existing PerceptionDecisionAdapter + DecisionEngine via
LivePerceptionSession.process_event().
"""
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.mission_service import get_mission_service

client = TestClient(app)


def _valid_payload():
    # S001 expects activity CHECK_EQUIPMENT + object experiment_container.
    # "experiment_container" passes object mapping + protocol validation;
    # hand near object (centers coincide) + high confidence yields a
    # CORRECT decision which advances S001 -> S002.
    return {
        "timestamp": "2026-09-22T00:00:00",
        "objects": [
            {
                "name": "experiment_container",
                "confidence": 0.95,
                "bbox": [100, 100, 200, 200],
            }
        ],
        "hands": [
            {"confidence": 0.95, "center": [150, 150]},
        ],
        "source": "camera",
    }


def test_post_valid_event_returns_real_decision():
    before = client.get("/api/mission/status").json()
    assert before["active"] is False
    assert before["status"] == "IDLE"
    assert before["event_count"] == 0

    r = client.post("/api/mission/event", json=_valid_payload())
    assert r.status_code == 200
    data = r.json()

    # Real result from the existing mission engine (not hand-computed).
    assert data["status"] == "CORRECT"
    assert data["step_id"] == "S001"
    assert data["next_step_id"] == "S002"
    assert data["perception"]["activity"] == "CHECK_EQUIPMENT"
    assert data["perception"]["object"] == "experiment_container"

    # Cross-check against the singleton session's last result.
    last = get_mission_service().session.get_last_result()
    assert last is not None
    assert last["status"] == data["status"]
    assert last["step_id"] == data["step_id"]


def test_event_count_increases_and_status_reflects_event():
    assert client.get("/api/mission/status").json()["event_count"] == 0

    r = client.post("/api/mission/event", json=_valid_payload())
    assert r.status_code == 200

    status = client.get("/api/mission/status").json()
    assert status["active"] is True
    assert status["event_count"] == 1
    assert status["activity"] == "CHECK_EQUIPMENT"
    assert status["detected_object"] == "experiment_container"
    assert status["status"] == "CORRECT"
    assert len(status["recent_events"]) == 1
    # Protocol progressed S001 (0/8) -> S002 (1/8).
    assert status["progress"]["current_step"] == "S002"
    assert status["progress"]["completed_steps"] == 1
    assert status["progress"]["total_steps"] == 8


def test_events_endpoint_returns_processed_event():
    client.post("/api/mission/event", json=_valid_payload())
    r = client.get("/api/events")
    assert r.status_code == 200
    events = r.json()
    assert isinstance(events, list)
    assert len(events) == 1
    assert events[0]["step_id"] == "S001"
    assert events[0]["activity"] == "CHECK_EQUIPMENT"


def test_summary_updates_after_post():
    before = client.get("/api/mission/summary").json()
    assert before["total_events"] == 0

    client.post("/api/mission/event", json=_valid_payload())

    after = client.get("/api/mission/summary").json()
    assert after["total_events"] == 1
    assert after["correct"] == 1


def test_invalid_source_rejected_with_422():
    payload = _valid_payload()
    payload["source"] = "synthetic"
    r = client.post("/api/mission/event", json=payload)
    assert r.status_code == 422
    # Rejected input must not advance the mission.
    assert client.get("/api/mission/status").json()["event_count"] == 0


def test_existing_get_endpoints_still_functional():
    client.post("/api/mission/event", json=_valid_payload())
    for path in (
        "/api/events",
        "/api/mission",
        "/api/mission/status",
        "/api/mission/progress",
        "/api/mission/summary",
        "/api/status",
        "/api/health",
    ):
        r = client.get(path)
        assert r.status_code == 200, path

    progress = client.get("/api/mission/progress").json()
    assert progress["total_steps"] == 8
    assert progress["completed_steps"] == 1


def test_reset_endpoint_starts_fresh_mission():
    # Advance the shared singleton once, then reset: the next mission
    # must start from the protocol's initial state with zero events.
    first = client.post("/api/mission/event", json=_valid_payload())
    assert first.status_code == 200
    assert first.json()["step_id"] == "S001"
    assert client.get("/api/mission/status").json()["event_count"] == 1

    reset = client.post("/api/mission/reset")
    assert reset.status_code == 200
    body = reset.json()
    assert body["reset"] is True
    assert body["status"]["active"] is False
    assert body["status"]["status"] == "IDLE"
    assert body["status"]["event_count"] == 0
    assert body["progress"]["current_step"] == "S001"
    assert body["progress"]["completed_steps"] == 0

    second = client.post("/api/mission/event", json=_valid_payload())
    assert second.status_code == 200
    assert second.json()["step_id"] == "S001"
    assert second.json()["status"] == "CORRECT"
    assert client.get("/api/mission/status").json()["event_count"] == 1
