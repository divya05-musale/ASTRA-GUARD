"""PerceptionEvent tests: structure, timestamp, source, empty lists."""
from agent.perception.perception_event import PerceptionEvent
import pytest


def test_valid_event():
    e = PerceptionEvent(timestamp="2026-01-01T10:00:00",
                        objects=[{"class_name": "bottle", "confidence": 0.91}],
                        hands=[{"handedness": "Right", "confidence": 0.88}])
    d = e.to_dict()
    assert d["source"] == "camera" and d["timestamp"] == "2026-01-01T10:00:00"
    assert len(d["objects"]) == 1 and len(d["hands"]) == 1


def test_auto_timestamp_and_empty_lists():
    e = PerceptionEvent()
    assert e.timestamp and e.objects == [] and e.hands == []
    assert e.to_dict()["source"] == "camera"


def test_bad_source_rejected():
    with pytest.raises(ValueError):
        PerceptionEvent(source="synthetic")
