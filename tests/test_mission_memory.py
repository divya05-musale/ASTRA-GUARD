from agent.memory.event_store import EventStore
from agent.memory.mission_memory import MissionMemory


def _make_memory():
    store = EventStore()

    store.record(
        step_id="S001",
        activity="CHECK_EQUIPMENT",
        detected_object="experiment_container",
        confidence=0.95,
        status="CORRECT",
    )

    store.record(
        step_id="S002",
        activity="RETRIEVE_SAMPLE",
        detected_object="wrong_object",
        confidence=0.90,
        status="DEVIATION",
        deviation="WRONG_OBJECT",
        guidance="Wrong object detected.",
    )

    store.record(
        step_id="S002",
        activity="RETRIEVE_SAMPLE",
        detected_object="biological_sample",
        confidence=0.40,
        status="UNCERTAIN",
        deviation="LOW_CONFIDENCE",
        guidance="Repeat detection.",
    )

    return MissionMemory(store)


def test_get_history():
    memory = _make_memory()

    history = memory.get_history()

    assert len(history) == 3
    assert history[0].step_id == "S001"
    assert history[1].status == "DEVIATION"
    assert history[2].status == "UNCERTAIN"


def test_get_recent():
    memory = _make_memory()

    recent = memory.get_recent(2)

    assert len(recent) == 2
    assert recent[0].status == "DEVIATION"
    assert recent[1].status == "UNCERTAIN"


def test_count_by_status():
    memory = _make_memory()

    counts = memory.count_by_status()

    assert counts["CORRECT"] == 1
    assert counts["DEVIATION"] == 1
    assert counts["UNCERTAIN"] == 1


def test_total_events():
    memory = _make_memory()

    assert memory.total_events() == 3


def test_summary():
    memory = _make_memory()

    summary = memory.get_summary()

    assert summary["total_events"] == 3
    assert summary["correct"] == 1
    assert summary["deviations"] == 1
    assert summary["uncertain"] == 1


def test_clear():
    memory = _make_memory()

    memory.clear()

    assert memory.total_events() == 0
    assert memory.get_history() == []