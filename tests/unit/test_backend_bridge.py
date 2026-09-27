"""Phase 13 → Phase 16 bridge tests (no network, no logic duplication)."""
import json
import urllib.error

import numpy as np

from agent.perception.backend_client import (
    BackendConnectionError,
    MissionBackendClient,
)
from agent.perception.live_processor import LivePerceptionProcessor
from agent.perception.perception_event import PerceptionEvent
from simulation.controlled_mission import (
    DEMO_MODE_BACKEND,
    DEMO_MODE_LOCAL,
    build_backend_client,
    create_event,
    get_backend_base_url,
    get_demo_mode,
    process_demo_event,
    reset_backend_mission,
)


class FakeObjectDetector:
    def detect(self, frame):
        return [{"class_name": "bottle", "confidence": 0.95}]


class FakeHandTracker:
    def process(self, frame):
        return [{"confidence": 0.9, "center": [10, 10]}]

    def close(self):
        pass


class FakeSession:
    def __init__(self):
        self.calls = 0

    def process_event(self, event):
        self.calls += 1
        return {"status": "LOCAL_OK"}


class FakeBackendClient:
    def __init__(self):
        self.received = None

    def post_event(self, event):
        self.received = event
        return {"status": "BACKEND_OK", "step_id": "S001"}


class FakeBackendClientWithReset(FakeBackendClient):
    def __init__(self):
        super().__init__()
        self.reset_calls = 0

    def reset_mission(self):
        self.reset_calls += 1
        return {"reset": True}


def test_reset_backend_mission_delegates_to_client():
    backend = FakeBackendClientWithReset()
    out = reset_backend_mission(backend)
    assert out == {"reset": True}
    assert backend.reset_calls == 1


def _frame():
    return np.zeros((4, 4, 3), dtype=np.uint8)


def test_client_serializes_with_to_dict():
    client = MissionBackendClient(base_url="http://127.0.0.1:8000/")
    assert client.event_url == "http://127.0.0.1:8000/api/mission/event"
    event = PerceptionEvent(timestamp="t", objects=[{"a": 1}], hands=[])
    payload = client.serialize_event(event)
    assert payload["source"] == "camera"
    assert payload["objects"] == [{"a": 1}]


def test_client_post_event_returns_parsed_json(monkeypatch):
    event = PerceptionEvent(timestamp="t", objects=[], hands=[])

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"status": "CORRECT"}).encode()

    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["data"] = json.loads(req.data.decode())
        return FakeResp()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    result = MissionBackendClient().post_event(event)
    assert result == {"status": "CORRECT"}
    assert captured["url"].endswith("/api/mission/event")
    assert captured["data"]["source"] == "camera"


def test_client_connection_error_when_backend_down(monkeypatch):
    def boom(req, timeout=None):
        raise urllib.error.URLError("refused")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    try:
        MissionBackendClient(timeout=1).post_event(
            PerceptionEvent(objects=[], hands=[])
        )
    except BackendConnectionError as exc:
        assert "127.0.0.1" in str(exc)
        assert "FastAPI" in str(exc)
    else:
        raise AssertionError("expected BackendConnectionError")


def test_client_reset_mission_posts_to_reset_endpoint(monkeypatch):
    captured = {}

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"reset": True}).encode()

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        return FakeResp()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    out = MissionBackendClient().reset_mission()
    assert out == {"reset": True}
    assert captured["url"].endswith("/api/mission/reset")
    assert captured["method"] == "POST"


def test_processor_local_mode_preserved():
    session = FakeSession()
    processor = LivePerceptionProcessor(
        FakeObjectDetector(), FakeHandTracker(), session
    )
    assert processor.use_backend is False
    out = processor.process_frame(_frame())
    assert out["result"] == {"status": "LOCAL_OK"}
    assert session.calls == 1


def test_processor_backend_mode_returns_backend_result():
    session = FakeSession()
    backend = FakeBackendClient()
    processor = LivePerceptionProcessor(
        FakeObjectDetector(), FakeHandTracker(), session, backend
    )
    assert processor.use_backend is True
    out = processor.process_frame(_frame())
    assert out["result"]["status"] == "BACKEND_OK"
    assert backend.received is out["event"]
    assert session.calls == 0


def test_processor_rejects_bad_backend_client():
    try:
        LivePerceptionProcessor(
            FakeObjectDetector(), FakeHandTracker(), FakeSession(),
            backend_client=object(),
        )
    except TypeError:
        assert True
    else:
        raise AssertionError("expected TypeError")


def test_demo_mode_helpers():
    assert get_demo_mode("backend") == DEMO_MODE_BACKEND
    assert get_demo_mode("LOCAL") == DEMO_MODE_LOCAL
    assert get_backend_base_url("http://x:9000") == "http://x:9000"
    url = build_backend_client("http://x:9000").event_url
    assert url.endswith("/api/mission/event")


def test_process_demo_event_local_and_backend():
    from agent.mission.live_perception_session import LivePerceptionSession
    from agent.mission.perception_decision import PerceptionDecisionAdapter
    from agent.mission.decision_engine import DecisionEngine
    from agent.mission.deviation_detector import DeviationDetector
    from agent.mission.sequence_validator import SequenceValidator
    from agent.mission.state_machine import ProtocolStateMachine
    from agent.mission.step_manager import StepManager

    steps = [
        {"step_id": "S001", "order": 1, "activity": "PICK_SAMPLE",
         "expected_object": "biological_sample", "timeout_sec": 30},
    ]
    acts = [{"activity_id": "PICK_SAMPLE"}]
    sm = ProtocolStateMachine(steps)
    engine = DecisionEngine(
        sm, StepManager(steps, sm),
        SequenceValidator(steps, acts), DeviationDetector(steps, acts),
    )
    session = LivePerceptionSession(PerceptionDecisionAdapter(engine))
    event = create_event("experiment_container")
    local = process_demo_event(session, event)
    assert local["status"] in ("CORRECT", "DEVIATION", "UNCERTAIN")
    backend = FakeBackendClient()
    out = process_demo_event(session, event, backend_client=backend)
    assert out["status"] == "BACKEND_OK"


def test_backend_mode_end_to_end_via_test_client():
    """Same event via HTTP bridge matches direct backend decision."""
    import urllib.request
    from fastapi.testclient import TestClient
    from backend.main import app
    from backend.services.mission_service import reset_mission_service
    from simulation.controlled_mission import DEMO_STEPS

    reset_mission_service()
    api = TestClient(app)
    client = MissionBackendClient(base_url="http://testserver")

    def fake_urlopen(req, timeout=None):
        path = req.full_url.replace("http://testserver", "")
        if req.data:
            resp = api.post(path, json=json.loads(req.data.decode()))
        else:
            resp = api.post(path)

        class R:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return json.dumps(resp.json()).encode()

        return R()

    old = urllib.request.urlopen
    urllib.request.urlopen = fake_urlopen
    try:
        # A fresh backend mission must show the full S001→S008 progression
        # (never S008/COMPLETED on every event from a stale session).
        assert client.reset_mission()["reset"] is True
        statuses = []
        steps = []
        for _, object_name, confidence, hand in DEMO_STEPS:
            result = client.post_event(
                create_event(
                    object_name,
                    confidence=confidence,
                    hand_interaction=hand,
                )
            )
            statuses.append(result["status"])
            steps.append(result["step_id"])
    finally:
        urllib.request.urlopen = old
    assert steps[0] == "S001"
    assert statuses[0] == "CORRECT"
    assert steps[2] == "S003"
    assert statuses[2] == "DEVIATION"
    assert steps[3] == "S003"
    assert statuses[3] == "UNCERTAIN"
    assert steps[-1] == "S008"
    assert statuses[-1] == "COMPLETED"
    assert api.get("/api/mission/status").json()["event_count"] == 10
    summary = api.get("/api/mission/summary").json()
    assert summary["total_events"] == 10
    assert summary["correct"] == 7
    assert summary["deviations"] == 1
    assert summary["uncertain"] == 1
    assert summary["completed"] == 1
    progress = api.get("/api/mission/progress").json()
    assert progress["completed_steps"] == 8
    assert progress["total_steps"] == 8
    assert progress["progress_percent"] == 100.0
    # A second run must start cleanly (no 20-event accumulation).
    reset_mission_service()
