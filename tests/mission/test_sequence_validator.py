"""Sequence validator tests using real EXP001 protocol."""
from agent.mission.protocol_loader import ProtocolLoader
from agent.mission.sequence_validator import SequenceValidator

EXP = "experiments/EXP001_TARDIGRADE"


def _validator():
    loader = ProtocolLoader(EXP).load()
    return SequenceValidator(loader.get_steps(), loader.get_activities())


def test_correct_event_is_valid():
    v = _validator()
    r = v.validate({"activity": "RETRIEVE_SAMPLE", "object": "biological_sample", "confidence": 0.95}, "S002")
    assert r["valid"] is True and r["reason"] is None
    assert r["activity_match"] and r["object_match"] and r["confidence_ok"]


def test_wrong_object():
    v = _validator()
    r = v.validate({"activity": "RETRIEVE_SAMPLE", "object": "wrong_sample", "confidence": 0.95}, "S002")
    assert r["valid"] is False and r["reason"] == "WRONG_OBJECT"
    assert r["activity_match"] is True and r["object_match"] is False


def test_wrong_activity():
    v = _validator()
    r = v.validate({"activity": "START_EXPERIMENT", "object": "experiment_controller", "confidence": 0.95}, "S003")
    assert r["valid"] is False and r["reason"] == "WRONG_SEQUENCE"


def test_low_confidence():
    v = _validator()
    r = v.validate({"activity": "RETRIEVE_SAMPLE", "object": "biological_sample", "confidence": 0.50}, "S002")
    assert r["valid"] is False and r["reason"] == "LOW_CONFIDENCE"
    assert r["confidence_ok"] is False


def test_unknown_activity():
    v = _validator()
    r = v.validate({"activity": "FLY_SPACESHIP", "object": "x", "confidence": 0.95}, "S002")
    assert r["valid"] is False and r["reason"] == "UNKNOWN_ACTION"

