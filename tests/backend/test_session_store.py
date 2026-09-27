import pytest

from backend.services.session_store import SessionStore


def test_session_record_survives_store_reopen(tmp_path):
    store = SessionStore(tmp_path)
    created = store.create({
        "experiment_id": "EXP001",
        "input_source": "webcam",
        "protocol": {"steps": [{"step_id": "S001"}]},
    })
    session_id = created["session_id"]
    event = {
        "decision_source": "automatic",
        "decision": {"status": "UNCERTAIN"},
    }

    store.append_event(session_id, event)
    assert SessionStore(tmp_path).list()[0]["event_count"] == 1
    store.update(session_id, {"status": "CANCELLED", "completed_at": "now"})

    reopened = SessionStore(tmp_path)
    record = reopened.get(session_id)
    assert record is not None
    assert record["status"] == "CANCELLED"
    assert record["events"] == [event]
    assert reopened.list()[0]["session_id"] == session_id
    assert reopened.list()[0]["event_count"] == 1
    assert list(tmp_path.glob("*.jsonl"))[0].read_text(encoding="utf-8").count("\n") == 1
    assert not list(tmp_path.glob("*.tmp"))


def test_session_store_rejects_invalid_session_ids(tmp_path):
    with pytest.raises(ValueError, match="Invalid session ID"):
        SessionStore(tmp_path).get("../outside")


def test_restart_marks_in_progress_sessions_interrupted(tmp_path):
    original = SessionStore(tmp_path)
    created = original.create({"experiment_id": "EXP001"})

    reopened = SessionStore(tmp_path)
    assert reopened.interrupt_in_progress() == 1
    recovered = reopened.get(created["session_id"])
    assert recovered["status"] == "INTERRUPTED"
    assert recovered["interruption_reason"] == "backend_restarted"


def test_repeat_updates_aggregate_without_adding_decision_rows(tmp_path):
    store = SessionStore(tmp_path)
    created = store.create({"experiment_id": "EXP001"})
    session_id = created["session_id"]
    store.append_event(session_id, {"timestamp": "event-1", "repeat_count": 1})

    assert store.append_repeat_update(session_id, "event-1", 12)
    record = store.get(session_id)

    assert record["event_count"] == 1
    assert record["events"] == [{"timestamp": "event-1", "repeat_count": 12}]
