from pathlib import Path

import pytest
from fastapi import HTTPException

from backend.api import experiments
from backend.services.session_store import SessionStore


@pytest.mark.parametrize(
    ("experiment_id", "expected_steps"),
    [("EXP001", 8), ("EXP006", 8)],
)
def test_registry_exposes_selectable_protocols(experiment_id, expected_steps):
    result = experiments.list_experiments()
    selected = next(
        item for item in result["experiments"]
        if item["experiment_id"] == experiment_id
    )

    assert selected["available"] is True
    assert selected["steps_count"] == expected_steps


@pytest.mark.parametrize("experiment_id", ["EXP001", "EXP006"])
def test_selection_loads_protocol_without_starting_a_session(monkeypatch, experiment_id):
    calls = []
    selected_service = type("Mission", (), {
        "experiment": {"experiment_id": experiment_id},
        "get_progress": lambda self: {"total_steps": 8, "current_step": "S001"},
    })()

    class IdleMission:
        active_session_id = None

    monkeypatch.setattr(experiments, "get_mission_service", lambda: IdleMission())
    monkeypatch.setattr(experiments, "find_valid_experiment", lambda _id: Path(experiment_id))
    monkeypatch.setattr(
        experiments,
        "reset_mission_service",
        lambda path: calls.append(("select", path)) or selected_service,
    )
    monkeypatch.setattr(
        experiments,
        "reset_protocol_service",
        lambda path: calls.append(("protocol", path)),
    )

    response = experiments.select_experiment(experiment_id)

    assert response["selected"] is True
    assert response["experiment"]["experiment_id"] == experiment_id
    assert response["progress"]["current_step"] == "S001"
    assert calls == [("select", Path(experiment_id)), ("protocol", Path(experiment_id))]


def test_selection_refuses_to_replace_an_in_progress_session(monkeypatch):
    class ActiveMission:
        active_session_id = "active-session"

        def get_session(self, _session_id):
            return {"status": "IN_PROGRESS"}

    reset_called = False

    def reset(_path):
        nonlocal reset_called
        reset_called = True

    monkeypatch.setattr(experiments, "get_mission_service", lambda: ActiveMission())
    monkeypatch.setattr(experiments, "find_valid_experiment", lambda _id: Path("EXP006"))
    monkeypatch.setattr(experiments, "reset_mission_service", reset)

    with pytest.raises(HTTPException) as error:
        experiments.select_experiment("EXP006")

    assert error.value.status_code == 409
    assert reset_called is False


def test_selection_preserves_completed_and_cancelled_session_history(monkeypatch, tmp_path):
    store = SessionStore(tmp_path / "sessions")
    records = []
    for status in ("COMPLETED", "CANCELLED"):
        record = store.create({
            "experiment_id": "EXP001",
            "input_source": "webcam",
            "evidence": [{"path": "saved-evidence.jpg", "kind": "image"}],
        })
        store.append_event(record["session_id"], {
            "timestamp": "2026-09-27T00:00:00+00:00",
            "decision": {"status": "CORRECT"},
        })
        store.update(record["session_id"], {"status": status})
        records.append(record["session_id"])

    selected_service = type("Mission", (), {
        "experiment": {"experiment_id": "EXP006"},
        "get_progress": lambda self: {"total_steps": 8, "current_step": "S001"},
    })()

    class IdleMission:
        active_session_id = None

    monkeypatch.setattr(experiments, "get_mission_service", lambda: IdleMission())
    monkeypatch.setattr(experiments, "find_valid_experiment", lambda _id: Path("EXP006"))
    monkeypatch.setattr(experiments, "reset_mission_service", lambda _path: selected_service)
    monkeypatch.setattr(experiments, "reset_protocol_service", lambda _path: None)

    assert experiments.select_experiment("EXP006")["selected"] is True
    saved = [store.get(session_id) for session_id in records]
    assert [record["status"] for record in saved] == ["COMPLETED", "CANCELLED"]
    assert [record["events"][0]["decision"]["status"] for record in saved] == ["CORRECT", "CORRECT"]
    assert all(record["evidence"][0]["path"] == "saved-evidence.jpg" for record in saved)