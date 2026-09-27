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

    return LivePerceptionSession(adapter)


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


def test_process_event():
    session = _make_session()

    result = session.process_event(_event())

    assert session.event_count == 1
    assert result["status"] == "CORRECT"


def test_last_result_is_stored():
    session = _make_session()

    result = session.process_event(_event())

    assert session.get_last_result() == result


def test_multiple_events_increment_counter():
    session = _make_session()

    session.process_event(_event())
    session.process_event(_event())

    assert session.event_count == 2


def test_reset():
    session = _make_session()

    session.process_event(_event())
    session.reset()

    assert session.event_count == 0
    assert session.get_last_result() is None


def test_reset_restores_protocol_state_machine():
    session = _make_session()

    result = session.process_event(_event())

    assert result["status"] == "CORRECT"
    assert session.adapter.engine.sm.current_step_id() == "S002"

    session.reset()

    assert session.adapter.engine.sm.current_step_id() == "S001"
    assert session.adapter.engine.sm.is_complete() is False
    assert session.adapter.engine.sm.step_index() == 0

    # A fresh mission must start from the initial protocol state again.
    result = session.process_event(_event())

    assert result["status"] == "CORRECT"
    assert result["step_id"] == "S001"


def test_invalid_event_rejected():
    session = _make_session()

    try:
        session.process_event({})
        assert False
    except TypeError:
        assert True