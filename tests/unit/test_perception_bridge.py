"""Unit tests for the ASTRA-GUARD Phase 7 perception bridge."""

from agent.mission.perception_bridge import (
    PerceptionProtocolBridge,
    ProtocolObservation,
)
from agent.perception.perception_event import PerceptionEvent


def make_event(objects=None, hands=None):
    """Create a simple synthetic perception event."""
    return PerceptionEvent(
        timestamp="2026-09-20T12:00:00",
        objects=objects or [],
        hands=hands or [],
        source="camera",
    )


def test_empty_event_returns_unknown():
    bridge = PerceptionProtocolBridge()

    event = make_event()

    observation = bridge.convert(event)

    assert isinstance(observation, ProtocolObservation)
    assert observation.activity == "UNKNOWN"
    assert observation.object is None
    assert observation.confidence == 0.0


def test_bottle_is_mapped_to_biological_sample():
    bridge = PerceptionProtocolBridge()

    event = make_event(
        objects=[
            {
                "name": "bottle",
                "confidence": 0.90,
                "bbox": [100, 100, 200, 200],
            }
        ]
    )

    observation = bridge.convert(event)

    assert observation.object == "biological_sample"
    assert observation.raw_object == "bottle"
    assert observation.activity == "OBJECT_PRESENT"


def test_hand_near_bottle_creates_pick_sample():
    bridge = PerceptionProtocolBridge()

    event = make_event(
        objects=[
            {
                "name": "bottle",
                "confidence": 0.90,
                "bbox": [100, 100, 200, 200],
            }
        ],
        hands=[
            {
                "confidence": 0.90,
                "center": [150, 150],
            }
        ],
    )

    observation = bridge.convert(event)

    assert observation.object == "biological_sample"
    assert observation.activity == "PICK_SAMPLE"
    assert 0.0 <= observation.confidence <= 1.0


def test_hand_far_from_bottle_does_not_create_pick_sample():
    bridge = PerceptionProtocolBridge()

    event = make_event(
        objects=[
            {
                "name": "bottle",
                "confidence": 0.90,
                "bbox": [100, 100, 200, 200],
            }
        ],
        hands=[
            {
                "confidence": 0.90,
                "center": [500, 500],
            }
        ],
    )

    observation = bridge.convert(event)

    assert observation.object == "biological_sample"
    assert observation.activity == "OBJECT_PRESENT"


def test_unknown_object_is_ignored():
    bridge = PerceptionProtocolBridge()

    event = make_event(
        objects=[
            {
                "name": "banana",
                "confidence": 0.95,
                "bbox": [100, 100, 200, 200],
            }
        ]
    )

    observation = bridge.convert(event)

    assert observation.activity == "UNKNOWN"
    assert observation.object is None


def test_low_confidence_object_is_ignored():
    bridge = PerceptionProtocolBridge()

    event = make_event(
        objects=[
            {
                "name": "bottle",
                "confidence": 0.20,
                "bbox": [100, 100, 200, 200],
            }
        ]
    )

    observation = bridge.convert(event)

    assert observation.activity == "UNKNOWN"
    assert observation.object is None


def test_confidence_is_clamped():
    bridge = PerceptionProtocolBridge()

    event = make_event(
        objects=[
            {
                "name": "bottle",
                "confidence": 1.0,
                "bbox": [100, 100, 200, 200],
            }
        ],
        hands=[
            {
                "confidence": 1.0,
                "center": [150, 150],
            }
        ],
    )

    observation = bridge.convert(event)

    assert 0.0 <= observation.confidence <= 1.0


def test_observation_to_dict():
    observation = ProtocolObservation(
        timestamp="test-time",
        activity="PICK_SAMPLE",
        object="biological_sample",
        confidence=0.85,
        source="camera",
        raw_object="bottle",
    )

    result = observation.to_dict()

    assert result["activity"] == "PICK_SAMPLE"
    assert result["object"] == "biological_sample"
    assert result["confidence"] == 0.85
    assert result["raw_object"] == "bottle"


def test_invalid_event_type_raises_error():
    bridge = PerceptionProtocolBridge()

    try:
        bridge.convert("invalid")
        assert False, "Expected TypeError"
    except TypeError:
        pass
def test_protocol_object_validator_accepts_supported_object():
    protocol_objects = [
        {"object_id": "biological_sample"},
        {"object_id": "sample_chamber"},
    ]

    bridge = PerceptionProtocolBridge(
        protocol_objects=protocol_objects
    )

    event = make_event(
        objects=[
            {
                "name": "bottle",
                "confidence": 0.90,
                "bbox": [100, 100, 200, 200],
            }
        ]
    )

    result = bridge.convert(event)

    assert result.object == "biological_sample"


def test_protocol_object_validator_rejects_unsupported_mapping():
    protocol_objects = [
        {"object_id": "sample_chamber"},
    ]

    bridge = PerceptionProtocolBridge(
        protocol_objects=protocol_objects
    )

    event = make_event(
        objects=[
            {
                "name": "bottle",
                "confidence": 0.90,
                "bbox": [100, 100, 200, 200],
            }
        ]
    )

    result = bridge.convert(event)

    assert result.object is None
    assert result.activity == "UNKNOWN"