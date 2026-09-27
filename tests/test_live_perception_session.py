from agent.memory.event_store import EventStore
from agent.memory.short_term_memory import ShortTermMemory
from agent.mission.decision_engine import DecisionEngine
from agent.mission.deviation_detector import DeviationDetector
from agent.mission.live_perception_session import LivePerceptionSession
from agent.mission.perception_decision import PerceptionDecisionAdapter
from agent.mission.sequence_validator import SequenceValidator
from agent.mission.state_machine import ProtocolStateMachine
from agent.mission.step_manager import StepManager
from agent.perception.perception_event import PerceptionEvent


def _make_session():
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
    step_manager = StepManager(steps, state_machine)
    validator = SequenceValidator(steps, activities)
    detector = DeviationDetector(steps, activities)

    engine = DecisionEngine(
        state_machine,
        step_manager,
        validator,
        detector,
    )

    adapter = PerceptionDecisionAdapter(engine)

    event_store = EventStore()
    short_term_memory = ShortTermMemory(capacity=3)

    return LivePerceptionSession(
        adapter,
        event_store=event_store,
        short_term_memory=short_term_memory,
    )


def _event():
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


def test_short_term_memory_receives_decision():
    session = _make_session()

    result = session.process_event(_event())

    recent = session.get_recent_events()

    assert result["status"] == "CORRECT"
    assert len(recent) == 1
    assert recent[0].step_id == "S001"
    assert recent[0].status == "CORRECT"


def test_event_store_and_short_term_memory_share_event():
    session = _make_session()

    session.process_event(_event())

    history_event = session.get_latest_event()
    recent_event = session.get_latest_recent_event()

    assert history_event is recent_event


def test_short_term_memory_keeps_recent_events_only():
    session = _make_session()

    session.process_event(_event())
    session.process_event(_event())
    session.process_event(_event())
    session.process_event(_event())

    recent = session.get_recent_events()
    history = session.get_event_history()

    assert len(history) == 4
    assert len(recent) == 3


def test_reset_clears_both_memory_layers():
    session = _make_session()

    session.process_event(_event())

    assert len(session.get_event_history()) == 1
    assert len(session.get_recent_events()) == 1

    session.reset()

    assert len(session.get_event_history()) == 0
    assert len(session.get_recent_events()) == 0
    assert session.get_latest_recent_event() is None