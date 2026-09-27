"""ObjectDetector tests: mocked YOLO, synthetic frames, no webcam/internet."""
from unittest.mock import MagicMock, patch
import numpy as np
import pytest
from agent.perception.object_detector import ObjectDetector


def _detector(names=None):
    fake = MagicMock()
    fake.names = names if names is not None else {0: "person", 39: "bottle"}
    fake.return_value = []
    with patch("agent.perception.object_detector.ObjectDetector._load_model",
               return_value=fake):
        det = ObjectDetector.__new__(ObjectDetector)
        det.model_path = "yolo11n.pt"
        det.confidence_threshold = 0.40
        det.device = None
        det._model = fake
    return det, fake


def _box(cls=39, conf=0.91, xyxy=(120, 80, 310, 420)):
    b = MagicMock()
    b.cls = [cls]
    b.conf = [conf]
    b.xyxy = [[float(v) for v in xyxy]]
    return b


def test_init_threshold_config():
    with patch("agent.perception.object_detector.ObjectDetector._load_model",
               return_value=MagicMock(names={})):
        d = ObjectDetector(model_path="yolo11n.pt", confidence_threshold=0.55)
        assert d.confidence_threshold == 0.55
    with pytest.raises(ValueError):
        with patch("agent.perception.object_detector.ObjectDetector._load_model",
                   return_value=MagicMock(names={})):
            ObjectDetector(confidence_threshold=1.5)


def test_missing_local_weights_fail_without_download(tmp_path):
    missing = tmp_path / "missing.pt"
    with pytest.raises(RuntimeError, match="Runtime model downloads are disabled"):
        ObjectDetector(model_path=str(missing))


def test_empty_result():
    det, fake = _detector()
    fake.return_value = []
    assert det.detect(np.zeros((480, 640, 3), dtype=np.uint8)) == []


def test_detection_structure():
    det, fake = _detector()
    r = MagicMock()
    r.boxes = [_box()]
    fake.return_value = [r]
    out = det.detect(np.zeros((480, 640, 3), dtype=np.uint8))
    assert len(out) == 1
    d = out[0]
    assert set(("class_id", "class_name", "confidence", "bbox", "center")) <= set(d)
    assert d["class_name"] == "bottle" and isinstance(d["class_id"], int)
    assert 0.0 <= d["confidence"] <= 1.0
    assert d["bbox"]["x2"] >= d["bbox"]["x1"] and d["bbox"]["y2"] >= d["bbox"]["y1"]
    assert d["center"] == {"x": 215.0, "y": 250.0}


def test_confidence_filtering():
    det, fake = _detector()
    r = MagicMock()
    r.boxes = [_box(conf=0.10)]
    fake.return_value = [r]
    assert det.detect(np.zeros((480, 640, 3), dtype=np.uint8)) == []


def test_draw_with_synthetic_detections():
    det, _ = _detector()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    dets = [{"class_id": 39, "class_name": "bottle", "confidence": 0.91,
             "bbox": {"x1": 10, "y1": 10, "x2": 100, "y2": 100},
             "center": {"x": 55, "y": 55}}]
    out = det.draw_detections(frame, dets)
    assert out.shape == frame.shape and np.any(out != 0) and np.all(frame == 0)


def test_invalid_frame_handling():
    det, _ = _detector()
    with pytest.raises(ValueError):
        det.detect(None)
    with pytest.raises(ValueError):
        det.draw_detections(None, [])
