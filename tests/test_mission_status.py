"""
Tests for Phase 11 MissionStatus.
"""

from agent.memory.event_store import EventStore
from agent.memory.short_term_memory import ShortTermMemory
from agent.mission.decision_engine import DecisionEngine
from agent.mission.deviation_detector import DeviationDetector
from agent.mission.live_perception_session import LivePerceptionSession
from agent.mission.mission_status import MissionStatus
from agent.mission.perception_decision import PerceptionDecisionAdapter
from agent.mission.sequence_validator import SequenceValidator
from agent.mission.state_machine import ProtocolStateMachine
from agent.mission.step_manager import StepManager
from agent.perception.perception_event import PerceptionEvent


def _make_session():
    """Create a real test mission session."""

    steps = [
        {
            "step_id": "S001",
            "order": 1,
            "activity": "PICK_SAMPLE",
            "expected_object": "biological_sample",
            "timeout_sec": 30,
        },
        {
            "step_id": "S002",
            "order": 2,
            "activity": "PLACE_SAMPLE",
            "expected_object": "sample_chamber",
            "timeout_sec": 30,
        },
    ]

    activities = [
        {"activity_id": "PICK_SAMPLE"},
        {"activity_id": "PLACE_SAMPLE"},
    ]

    state_machine = ProtocolStateMachine(steps)

    step_manager = StepManager(
        steps,
        state_machine,
    )

    validator = SequenceValidator(
        steps,
        activities,
    )

    detector = DeviationDetector(
        steps,
        activities,
    )

    engine = DecisionEngine(
        state_machine,
        step_manager,
        validator,
        detector,
    )

    adapter = PerceptionDecisionAdapter(
        engine,
    )

    event_store = EventStore()

    short_term_memory = ShortTermMemory(
        capacity=3,
    )

    return LivePerceptionSession(
        adapter,
        event_store=event_store,
        short_term_memory=short_term_memory,
    )


def _event():
    """Create a test perception event."""

    return PerceptionEvent(
        timestamp="2026-09-20T12:00:00",
        source="camera",
        objects=[
            {
                "name": "bottle",
                "confidence": 0.95,
                "bbox": [100, 100, 200, 200],
            }
        ],
        hands=[
            {
                "confidence": 0.95,
                "center": [150, 150],
            }
        ],
    )


def test_mission_status_requires_session():
    """MissionStatus must require a LivePerceptionSession."""

    try:
        MissionStatus(None)
        assert False
    except TypeError:
        assert True


def test_empty_session_returns_idle_status():
    """A new session should report IDLE status."""

    session = _make_session()

    status = MissionStatus(session)

    result = status.get_current_status()

    assert result["active"] is False
    assert result["step_id"] is None
    assert result["status"] == "IDLE"
    assert result["event_count"] == 0
    assert result["recent_events"] == []


def test_empty_session_summary():
    """A new session should have an empty summary."""

    session = _make_session()

    status = MissionStatus(session)

    result = status.get_summary()

    assert result["total_events"] == 0
    assert result["correct"] == 0
    assert result["deviations"] == 0
    assert result["uncertain"] == 0
    assert result["completed"] == 0


def test_event_count_reads_from_session():
    """MissionStatus should expose the session event count."""

    session = _make_session()

    status = MissionStatus(session)

    assert status.get_event_count() == 0

    session.process_event(_event())

    assert status.get_event_count() == 1


def test_recent_events_empty():
    """A new session should have no recent events."""

    session = _make_session()

    status = MissionStatus(session)

    assert status.get_recent_events() == []


def test_current_status_after_event():
    """MissionStatus should expose the latest mission decision."""

    session = _make_session()

    status = MissionStatus(session)

    session.process_event(_event())

    result = status.get_current_status()

    assert result["active"] is True
    assert result["step_id"] == "S001"
    assert result["status"] == "CORRECT"
    assert result["event_count"] == 1
    assert len(result["recent_events"]) == 1


def test_summary_after_correct_event():
    """Mission summary should count a correct decision."""

    session = _make_session()

    status = MissionStatus(session)

    session.process_event(_event())

    result = status.get_summary()

    assert result["total_events"] == 1
    assert result["correct"] == 1
    assert result["deviations"] == 0
    assert result["uncertain"] == 0


def test_recent_events_limit():
    """Recent events should respect the requested limit."""

    session = _make_session()

    status = MissionStatus(session)

    session.process_event(_event())
    session.process_event(_event())
    session.process_event(_event())

    events = status.get_recent_events(limit=2)

    assert len(events) == 2


def test_recent_events_zero_limit():
    """A zero limit should return no events."""

    session = _make_session()

    status = MissionStatus(session)

    session.process_event(_event())

    assert status.get_recent_events(limit=0) == []

def test_initial_mission_progress():
    """A new mission should start at the first step."""

    session = _make_session()

    status = MissionStatus(session)

    progress = status.get_progress()

    assert progress["current_step"] == "S001"
    assert progress["current_index"] == 0
    assert progress["completed_steps"] == 0
    assert progress["total_steps"] == 2
    assert progress["progress_percent"] == 0.0
    assert progress["completed"] is False


def test_progress_after_correct_event():
    """Progress should advance after a correct decision."""

    session = _make_session()

    status = MissionStatus(session)

    session.process_event(_event())

    progress = status.get_progress()

    assert progress["current_step"] == "S002"
    assert progress["current_index"] == 1
    assert progress["completed_steps"] == 1
    assert progress["total_steps"] == 2
    assert progress["progress_percent"] == 50.0
    assert progress["completed"] is False


def test_current_status_contains_progress():
    """Current status should include mission progress."""

    session = _make_session()

    status = MissionStatus(session)

    result = status.get_current_status()

    assert "progress" in result
    assert result["progress"]["current_step"] == "S001"
    assert result["progress"]["total_steps"] == 2