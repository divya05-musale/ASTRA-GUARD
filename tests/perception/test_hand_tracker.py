"""HandTracker tests: synthetic frames / mocked MediaPipe, no webcam."""
from unittest.mock import MagicMock, patch
import numpy as np
from agent.perception.hand_tracker import HandTracker


def _tracker_with_fake(fake_hands):
    with patch("agent.perception.hand_tracker.HandTracker._init_tracker",
               lambda self: None):
        t = HandTracker.__new__(HandTracker)
        t.max_num_hands = 2
        t.detection_confidence = 0.5
        t.tracking_confidence = 0.5
        t._hands = fake_hands
        t._mp_hands_mod = MagicMock()
        t._mp_draw = MagicMock()
    return t


def _landmarks(n=21):
    pts = []
    for i in range(n):
        p = MagicMock()
        p.x, p.y, p.z = 0.1 + i * 0.01, 0.2 + i * 0.01, 0.01
        pts.append(p)
    hand = MagicMock()
    hand.landmark = pts
    return hand


def test_init_params():
    with patch("agent.perception.hand_tracker.HandTracker._init_tracker",
               lambda self: setattr(self, "_hands", MagicMock()) or
               setattr(self, "_mp_hands_mod", None) or setattr(self, "_mp_draw", None)):
        t = HandTracker(max_num_hands=1, detection_confidence=0.6, tracking_confidence=0.7)
        assert (t.max_num_hands, t.detection_confidence) == (1, 0.6)
        t.close()


def test_no_hand_result():
    fake = MagicMock()
    res = MagicMock()
    res.multi_hand_landmarks = []
    res.multi_handedness = []
    fake.process.return_value = res
    t = _tracker_with_fake(fake)
    assert t.process(np.zeros((480, 640, 3), dtype=np.uint8)) == []
    t.close()


def test_hand_structure_and_landmarks():
    fake = MagicMock()
    res = MagicMock()
    res.multi_hand_landmarks = [_landmarks()]
    cls = MagicMock()
    cls.label, cls.score = "Right", 0.88
    h = MagicMock()
    h.classification = [cls]
    res.multi_handedness = [h]
    fake.process.return_value = res
    t = _tracker_with_fake(fake)
    out = t.process(np.zeros((480, 640, 3), dtype=np.uint8))
    assert len(out) == 1 and out[0]["handedness"] == "Right"
    assert len(out[0]["landmarks"]) == 21
    lm0 = out[0]["landmarks"][0]
    assert set(("x", "y", "z")) <= set(lm0) and all(isinstance(v, float) for v in lm0.values())
    drawn = t.draw_landmarks(np.zeros((480, 640, 3), dtype=np.uint8), out)
    assert drawn.shape == (480, 640, 3)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    annotated_in_place = t.draw_landmarks(frame, out, copy_frame=False)
    assert annotated_in_place is frame
    assert np.any(frame != 0)
    t.close()
