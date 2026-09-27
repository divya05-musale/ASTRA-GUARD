from agent.memory.event_store import MissionEvent
from agent.memory.short_term_memory import ShortTermMemory


def _event(step_id: str) -> MissionEvent:
    return MissionEvent(
        timestamp="2026-09-20T12:00:00",
        step_id=step_id,
        activity="TEST_ACTIVITY",
        detected_object="test_object",
        confidence=0.95,
        status="CORRECT",
        deviation=None,
        guidance="Continue.",
    )


def test_add_event():
    memory = ShortTermMemory()

    memory.add(_event("S001"))

    assert memory.count() == 1
    assert memory.get_latest().step_id == "S001"


def test_events_are_kept_in_order():
    memory = ShortTermMemory()

    memory.add(_event("S001"))
    memory.add(_event("S002"))
    memory.add(_event("S003"))

    recent = memory.get_recent()

    assert [event.step_id for event in recent] == [
        "S001",
        "S002",
        "S003",
    ]


def test_capacity_removes_oldest_event():
    memory = ShortTermMemory(capacity=2)

    memory.add(_event("S001"))
    memory.add(_event("S002"))
    memory.add(_event("S003"))

    recent = memory.get_recent()

    assert len(recent) == 2
    assert [event.step_id for event in recent] == [
        "S002",
        "S003",
    ]


def test_empty_memory():
    memory = ShortTermMemory()

    assert memory.count() == 0
    assert memory.get_recent() == []
    assert memory.get_latest() is None


def test_clear():
    memory = ShortTermMemory()

    memory.add(_event("S001"))
    memory.add(_event("S002"))

    memory.clear()

    assert memory.count() == 0
    assert memory.get_recent() == []
    assert memory.get_latest() is None


def test_invalid_event_rejected():
    memory = ShortTermMemory()

    try:
        memory.add({})
        assert False
    except TypeError:
        assert True