"""Deviation detector tests using real EXP001 protocol."""
from agent.mission.protocol_loader import ProtocolLoader
from agent.mission.deviation_detector import DeviationDetector

EXP = "experiments/EXP001_TARDIGRADE"


def _detector():
    loader = ProtocolLoader(EXP).load()
    return DeviationDetector(loader.get_steps(), loader.get_activities())


def test_wrong_object():
    d = _detector()
    r = d.detect({"activity": "RETRIEVE_SAMPLE", "object": "wrong_sample", "confidence": 0.95}, "S002")
    assert r["deviation_type"] == "WRONG_OBJECT"


def test_wrong_sequence():
    d = _detector()
    r = d.detect({"activity": "TRANSFER_SAMPLE", "object": "sample_chamber", "confidence": 0.95}, "S003")
    assert r["deviation_type"] == "WRONG_SEQUENCE"


def test_low_confidence():
    d = _detector()
    r = d.detect({"activity": "RETRIEVE_SAMPLE", "object": "biological_sample", "confidence": 0.50}, "S002")
    assert r["deviation_type"] == "LOW_CONFIDENCE"


def test_unknown_action():
    d = _detector()
    r = d.detect({"activity": "FLY_SPACESHIP", "object": "x", "confidence": 0.95}, "S002")
    assert r["deviation_type"] == "UNKNOWN_ACTION"


def test_recovery_after_deviation():
    d = _detector()
    bad = d.detect({"activity": "RETRIEVE_SAMPLE", "object": "wrong_sample", "confidence": 0.95}, "S002")
    assert bad["deviation_type"] == "WRONG_OBJECT"
    good = d.detect({"activity": "RETRIEVE_SAMPLE", "object": "biological_sample", "confidence": 0.95}, "S002")
    assert good["deviation_type"] == "RECOVERED" and good["recovered"] is True

