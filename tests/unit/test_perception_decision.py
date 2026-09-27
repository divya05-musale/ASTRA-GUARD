"""Tests for Phase 7.3 perception-to-decision integration."""

from agent.mission.decision_engine import DecisionEngine
from agent.mission.deviation_detector import DeviationDetector
from agent.mission.perception_bridge import PerceptionProtocolBridge
from agent.mission.perception_decision import PerceptionDecisionAdapter
from agent.mission.sequence_validator import SequenceValidator
from agent.mission.state_machine import ProtocolStateMachine
from agent.mission.step_manager import StepManager
from agent.mission.protocol_loader import ProtocolLoader
from agent.perception.perception_event import PerceptionEvent


EXP = "experiments/EXP001_TARDIGRADE"


def _make_adapter():
    loader = ProtocolLoader(EXP).load()

    steps = loader.get_steps()
    activities = loader.get_activities()
    rules = loader.get_rules()

    sm = ProtocolStateMachine(steps)
    manager = StepManager(steps, sm, rules)
    validator = SequenceValidator(steps, activities)
    detector = DeviationDetector(steps, activities)

    engine = DecisionEngine(
        sm,
        manager,
        validator,
        detector,
        rules,
    )

    adapter = PerceptionDecisionAdapter(
        engine,
        PerceptionProtocolBridge(),
    )

    return adapter, sm


def _event(
    objects,
    hands=None,
    timestamp="2026-09-20T12:00:00",
):
    return PerceptionEvent(
        timestamp=timestamp,
        source="camera",
        objects=objects,
        hands=hands or [],
    )


def test_adapter_creates_protocol_observation():
    adapter, _ = _make_adapter()

    event = _event(
        [
            {
                "name": "bottle",
                "confidence": 0.95,
                "bbox": [100, 100, 200, 200],
            }
        ]
    )

    observation = adapter.observe(event)

    assert observation.object == "biological_sample"
    assert observation.activity == "OBJECT_PRESENT"
    assert observation.confidence == 0.95


def test_unknown_object_becomes_unknown_action():
    adapter, sm = _make_adapter()

    event = _event(
        [
            {
                "name": "laptop",
                "confidence": 0.95,
                "bbox": [100, 100, 200, 200],
            }
        ]
    )

    result = adapter.decide(event)

    assert result["status"] == "DEVIATION"
    assert result["deviation_type"] == "UNKNOWN_ACTION"

    # Decision engine must not advance.
    assert sm.current_step_id() == "S001"


def test_low_confidence_perception_becomes_deviation():
    adapter, sm = _make_adapter()

    event = _event(
        [
            {
                "name": "bottle",
                "confidence": 0.20,
                "bbox": [100, 100, 200, 200],
            }
        ]
    )

    result = adapter.decide(event)

    assert result["status"] == "DEVIATION"
    assert result["deviation_type"] == "UNKNOWN_ACTION"
    assert result["perception"]["activity"] == "UNKNOWN"
    assert result["perception"]["object"] is None


def test_decision_contains_perception_information():
    adapter, _ = _make_adapter()

    event = _event(
        [
            {
                "name": "bottle",
                "confidence": 0.90,
                "bbox": [100, 100, 200, 200],
            }
        ]
    )

    result = adapter.decide(event)

    assert "perception" in result
    assert result["perception"]["object"] == "biological_sample"
    assert result["perception"]["raw_object"] == "bottle"


def test_invalid_event_type_is_rejected():
    adapter, _ = _make_adapter()

    try:
        adapter.decide({"activity": "PICK_SAMPLE"})
        assert False
    except TypeError:
        assert True