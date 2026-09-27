import numpy as np
import pytest

from agent.mission.decision_engine import DecisionEngine
from agent.mission.deviation_detector import DeviationDetector
from agent.mission.live_perception_session import LivePerceptionSession
from agent.mission.perception_decision import PerceptionDecisionAdapter
from agent.mission.sequence_validator import SequenceValidator
from agent.mission.state_machine import ProtocolStateMachine
from agent.mission.step_manager import StepManager
from agent.perception.live_processor import LivePerceptionProcessor
from agent.perception.object_detector import ObjectDetector
from agent.perception.hand_tracker import HandTracker


class FakeObjectDetector:
    def detect(self, frame):
        return [
            {
                "class_name": "bottle",
                "confidence": 0.95,
                "bbox": {
                    "x1": 100.0,
                    "y1": 100.0,
                    "x2": 200.0,
                    "y2": 200.0,
                },
            }
        ]


class FakeHandTracker:
    def process(self, frame):
        return [{
            "hand_index": 0,
            "handedness": "Right",
            "confidence": 0.95,
            "center": [150.0, 150.0],
            "landmarks": [{"x": 0.117, "y": 0.208, "z": 0.0}],
        }]

    def close(self):
        pass


class FakeSession:
    def __init__(self):
        self.received_event = None

    def process_event(self, event):
        self.received_event = event

        return {
            "status": "CORRECT",
            "step_id": "S001",
        }


def _make_real_session():
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

    adapter = PerceptionDecisionAdapter(engine)

    return LivePerceptionSession(adapter)


def test_process_frame_creates_perception_event():
    processor = LivePerceptionProcessor(
        FakeObjectDetector(),
        FakeHandTracker(),
        FakeSession(),
    )

    frame = np.zeros(
        (720, 1280, 3),
        dtype=np.uint8,
    )

    result = processor.process_frame(frame)

    assert result["event"].source == "camera"
    assert len(result["event"].objects) == 1
    assert len(result["event"].hands) == 1


def test_object_and_hand_data_reach_session():
    session = FakeSession()

    processor = LivePerceptionProcessor(
        FakeObjectDetector(),
        FakeHandTracker(),
        session,
    )

    frame = np.zeros(
        (720, 1280, 3),
        dtype=np.uint8,
    )

    processor.process_frame(frame)

    assert session.received_event is not None
    assert session.received_event.objects[0]["class_name"] == "bottle"
    assert session.received_event.hands[0]["handedness"] == "Right"


def test_processor_returns_session_result():
    processor = LivePerceptionProcessor(
        FakeObjectDetector(),
        FakeHandTracker(),
        FakeSession(),
    )

    frame = np.zeros(
        (720, 1280, 3),
        dtype=np.uint8,
    )

    result = processor.process_frame(frame)

    assert result["result"]["status"] == "CORRECT"


def test_invalid_frame_rejected():
    processor = LivePerceptionProcessor(
        FakeObjectDetector(),
        FakeHandTracker(),
        FakeSession(),
    )

    with pytest.raises(ValueError):
        processor.process_frame(None)


def test_real_session_receives_perception():
    session = _make_real_session()

    processor = LivePerceptionProcessor(
        FakeObjectDetector(),
        FakeHandTracker(),
        session,
    )

    frame = np.zeros(
        (720, 1280, 3),
        dtype=np.uint8,
    )

    result = processor.process_frame(frame)

    assert result["event"].objects
    assert result["event"].hands
    assert result["result"]["status"] == "CORRECT"