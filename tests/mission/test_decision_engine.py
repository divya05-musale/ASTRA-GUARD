"""Decision engine tests using real EXP001 protocol."""
from agent.mission.protocol_loader import ProtocolLoader
from agent.mission.state_machine import ProtocolStateMachine
from agent.mission.step_manager import StepManager
from agent.mission.sequence_validator import SequenceValidator
from agent.mission.deviation_detector import DeviationDetector
from agent.mission.decision_engine import DecisionEngine

EXP = "experiments/EXP001_TARDIGRADE"

CORRECT = [
    ("S001", "CHECK_EQUIPMENT", "experiment_container"),
    ("S002", "RETRIEVE_SAMPLE", "biological_sample"),
    ("S003", "OPEN_CONTAINER", "sample_chamber"),
    ("S004", "TRANSFER_SAMPLE", "sample_chamber"),
    ("S005", "START_EXPERIMENT", "experiment_controller"),
    ("S006", "RECORD_RESULT", "observation_interface"),
    ("S007", "SECURE_SAMPLE", "sample_chamber"),
    ("S008", "COMPLETE_EXPERIMENT", "experiment_controller"),
]


def _engine():
    loader = ProtocolLoader(EXP).load()
    steps, acts, rules = loader.get_steps(), loader.get_activities(), loader.get_rules()
    sm = ProtocolStateMachine(steps)
    mgr = StepManager(steps, sm, rules)
    val = SequenceValidator(steps, acts)
    det = DeviationDetector(steps, acts)
    eng = DecisionEngine(sm, mgr, val, det, rules)
    return eng, sm


def test_correct_event_advances_state():
    eng, sm = _engine()
    out = eng.process({"activity": "CHECK_EQUIPMENT", "object": "experiment_container", "confidence": 0.95})
    assert out["status"] == "CORRECT" and out["step_id"] == "S001"
    assert out["next_step_id"] == "S002" and sm.current_step_id() == "S002"


def test_wrong_object_does_not_advance():
    eng, sm = _engine()
    eng.process({"activity": "CHECK_EQUIPMENT", "object": "experiment_container", "confidence": 0.95})
    out = eng.process({"activity": "RETRIEVE_SAMPLE", "object": "wrong_sample", "confidence": 0.95})
    assert out["status"] == "DEVIATION" and out["deviation_type"] == "WRONG_OBJECT"
    assert sm.current_step_id() == "S002" and out["next_step_id"] == "S002"


def test_wrong_activity_does_not_advance():
    eng, sm = _engine()
    out = eng.process({"activity": "START_EXPERIMENT", "object": "experiment_controller", "confidence": 0.95})
    assert out["status"] == "DEVIATION" and sm.current_step_id() == "S001"


def test_low_confidence_does_not_advance():
    eng, sm = _engine()
    out = eng.process({"activity": "CHECK_EQUIPMENT", "object": "experiment_container", "confidence": 0.50})
    assert out["status"] == "UNCERTAIN" and out["deviation_type"] == "LOW_CONFIDENCE"
    assert sm.current_step_id() == "S001"


def test_final_correct_event_returns_completed():
    eng, sm = _engine()
    last = None
    for sid, act, obj in CORRECT:
        last = eng.process({"activity": act, "object": obj, "confidence": 0.95})
    assert last["status"] == "COMPLETED"
    assert sm.is_complete() is True

