from pathlib import Path

import cv2
import numpy as np

from agent.perception.experiment_object_detector import ExperimentObjectDetector


ROOT = Path(__file__).resolve().parents[2]


class EmptyDetector:
    names = {}

    def detect(self, _frame):
        return []

    def draw_detections(self, frame, _detections):
        return frame.copy()


def _detector(experiment_dir):
    return ExperimentObjectDetector(EmptyDetector(), ROOT / "experiments" / experiment_dir)


def _payload_frame(red_bounds=(60, 100, 180, 260), yellow_bounds=(380, 100, 500, 260)):
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    x1, y1, x2, y2 = red_bounds
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), -1)
    x1, y1, x2, y2 = yellow_bounds
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), -1)
    return frame


def test_payload_detector_reports_colors_and_configured_zones():
    detector = _detector("EXP006_PAYLOAD_TRANSFER")
    detections = detector.detect(_payload_frame())
    by_name = {item["name"]: item for item in detections}

    assert by_name["red_box"]["metadata"]["zone"] == "zone_a"
    assert by_name["red_box"]["metadata"]["fully_inside_zone"] is True
    assert by_name["yellow_box"]["metadata"]["zone"] == "zone_b"
    assert by_name["yellow_box"]["metadata"]["fully_inside_zone"] is True
    assert "both_boxes_verified" not in by_name


def test_payload_detector_flags_wrong_zone_from_pixels():
    detector = _detector("EXP006_PAYLOAD_TRANSFER")
    detections = detector.detect(_payload_frame(
        red_bounds=(400, 100, 500, 240),
        yellow_bounds=(520, 100, 600, 240),
    ))
    red = next(item for item in detections if item["name"] == "red_box")

    assert red["metadata"]["protocol_violation"] == "WRONG_ZONE"
    assert "zone a" in red["metadata"]["guidance"].lower()


def test_payload_detector_rejects_box_outside_all_zones():
    detector = _detector("EXP006_PAYLOAD_TRANSFER")
    detections = detector.detect(_payload_frame(
        red_bounds=(0, 100, 20, 160),
        yellow_bounds=(520, 100, 600, 240),
    ))
    red = next(item for item in detections if item["name"] == "red_box")

    assert red["metadata"]["protocol_violation"] == "BOX_NOT_FULLY_IN_ZONE"


def test_payload_open_rack_requires_configured_aruco_marker_13():
    detector = _detector("EXP006_PAYLOAD_TRANSFER")
    frame = np.full((480, 640, 3), 255, dtype=np.uint8)
    marker = _marker(13, side=180)
    marker_bgr = cv2.cvtColor(marker, cv2.COLOR_GRAY2BGR)
    frame[120:120 + marker_bgr.shape[0], 220:220 + marker_bgr.shape[1]] = marker_bgr

    detections = detector.detect(frame)
    rack = next(item for item in detections if item["name"] == "rack_opened")

    assert rack["confidence"] == 1.0
    assert rack["metadata"]["marker_id"] == 13


def test_payload_hold_requires_one_source_second():
    detector = _detector("EXP006_PAYLOAD_TRANSFER")
    frame = _payload_frame()
    red_states = []
    for frame_index in range(31):
        detector.set_frame_timestamp(10.0 + frame_index / 30.0)
        detections = detector.detect(frame)
        red_states.append(next(item for item in detections if item["name"] == "red_box")["metadata"])

    assert red_states[0]["uncertainty_reason"] == "HOLD_NOT_MET"
    assert red_states[-1]["held_seconds"] >= 1.0
    assert "uncertainty_reason" not in red_states[-1]


def _marker(marker_id, side=80):
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker = cv2.aruco.generateImageMarker(dictionary, marker_id, side)
    padded = np.full((side + 20, side + 20), 255, dtype=np.uint8)
    padded[10:-10, 10:-10] = marker
    return padded


def test_plant_markers_require_real_aruco_and_hand_for_simulated_watering():
    detector = _detector("EXP007_PLANT_MONITORING")
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    for marker_id, x in ((10, 50), (11, 150), (12, 250)):
        marker = _marker(marker_id)
        marker_height, marker_width = marker.shape
        frame[100:100 + marker_height, x:x + marker_width] = cv2.cvtColor(marker, cv2.COLOR_GRAY2BGR)

    detections = detector.detect(frame)
    ids = {item.get("metadata", {}).get("marker_id") for item in detections}
    assert {10, 11, 12} <= ids
    assert not any(item["name"] == "simulated_watering" for item in detections)

    detector.apply_hand_context(detections, [{"center": [300.0, 150.0], "confidence": 0.92}], frame.shape)
    watering = next(item for item in detections if item["name"] == "simulated_watering")
    assert watering["confidence"] == 0.92
    assert watering["metadata"]["method"] == "marker_and_hand_proximity_simulation"
    assert watering["metadata"]["water_quantity_measured"] is False
