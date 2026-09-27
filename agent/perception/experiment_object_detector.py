"""Local, configurable perception strategies for supported experiments."""

from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import cv2
import numpy as np

from agent.mission.protocol_loader import ProtocolLoader


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ExperimentObjectDetector:
    """Combine the existing YOLO detector with local configured visual cues."""

    def __init__(
        self,
        base_detector: Any,
        experiment_path: str | Path,
        protocol_client: Any | None = None,
        refresh_interval: float = 1.0,
    ) -> None:
        if not hasattr(base_detector, "detect") or not hasattr(base_detector, "draw_detections"):
            raise TypeError("base_detector must provide detect and draw_detections")
        self.base_detector = base_detector
        self.experiment_path = Path(experiment_path)
        self.protocol_client = protocol_client
        self.refresh_interval = max(0.25, float(refresh_interval))
        self._last_protocol_poll = 0.0
        self._experiment: Dict[str, Any] = {}
        self._steps: list[Dict[str, Any]] = []
        self._hold_state: Dict[str, tuple[str, float, float, int]] = {}
        self._last_detection_timestamp = time.monotonic()
        self._load_protocol(self.experiment_path)

    @property
    def names(self):
        return getattr(self.base_detector, "names", {})

    def _load_protocol(self, path: Path) -> None:
        protocol = ProtocolLoader(path).load()
        self._experiment = protocol.get_experiment()
        self._steps = protocol.get_steps()
        self.experiment_path = path
        self._hold_state.clear()

    def set_frame_timestamp(self, timestamp: float) -> None:
        self._last_detection_timestamp = float(timestamp)

    def _refresh_protocol(self) -> None:
        if self.protocol_client is None:
            return
        now = time.monotonic()
        if now - self._last_protocol_poll < self.refresh_interval:
            return
        self._last_protocol_poll = now
        try:
            response = self.protocol_client.get_protocol()
            experiment = response.get("experiment") or {}
            experiment_id = str(experiment.get("experiment_id") or "")
        except Exception:
            return
        if not experiment_id or experiment_id == str(self._experiment.get("experiment_id")):
            return
        for candidate in sorted((PROJECT_ROOT / "experiments").glob("EXP*")):
            try:
                protocol = ProtocolLoader(candidate).load()
            except (OSError, KeyError, TypeError, ValueError):
                continue
            if str(protocol.get_experiment().get("experiment_id")) == experiment_id:
                self._load_protocol(candidate)
                break

    @staticmethod
    def _box(name: str, confidence: float, bounds: tuple[int, int, int, int], **metadata) -> Dict[str, Any]:
        x1, y1, x2, y2 = bounds
        return {
            "name": name,
            "class_name": name,
            "confidence": max(0.0, min(1.0, float(confidence))),
            "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
            "center": {"x": (x1 + x2) / 2.0, "y": (y1 + y2) / 2.0},
            "metadata": metadata,
        }

    @staticmethod
    def _dictionary(dictionary_name: str):
        aruco = getattr(cv2, "aruco", None)
        if aruco is None or not hasattr(aruco, dictionary_name):
            raise RuntimeError("This OpenCV installation does not provide the configured ArUco dictionary")
        return aruco.getPredefinedDictionary(getattr(aruco, dictionary_name))

    def _detect_markers(self, frame: np.ndarray, mapping: Dict[int, str], dictionary_name: str) -> list[Dict[str, Any]]:
        if not mapping:
            return []
        aruco = cv2.aruco
        detector = aruco.ArucoDetector(self._dictionary(dictionary_name), aruco.DetectorParameters())
        corners, marker_ids, _rejected = detector.detectMarkers(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
        if marker_ids is None:
            return []
        detections = []
        for points, marker_id_value in zip(corners, marker_ids.flatten()):
            marker_id = int(marker_id_value)
            object_name = mapping.get(marker_id)
            if not object_name:
                continue
            polygon = np.asarray(points, dtype=np.float32).reshape(-1, 2)
            x1 = max(0, int(np.floor(polygon[:, 0].min())))
            y1 = max(0, int(np.floor(polygon[:, 1].min())))
            x2 = min(frame.shape[1], int(np.ceil(polygon[:, 0].max())))
            y2 = min(frame.shape[0], int(np.ceil(polygon[:, 1].max())))
            detections.append(self._box(object_name, 1.0, (x1, y1, x2, y2), marker_id=marker_id))
        return detections

    @staticmethod
    def _mask_from_ranges(hsv: np.ndarray, ranges: Iterable[Iterable[int]]) -> np.ndarray:
        masks = []
        for values in ranges:
            bounds = [int(value) for value in values]
            if len(bounds) != 6:
                continue
            low = np.array(bounds[:3], dtype=np.uint8)
            high = np.array(bounds[3:], dtype=np.uint8)
            masks.append(cv2.inRange(hsv, low, high))
        if not masks:
            return np.zeros(hsv.shape[:2], dtype=np.uint8)
        result = masks[0]
        for mask in masks[1:]:
            result = cv2.bitwise_or(result, mask)
        kernel = np.ones((3, 3), dtype=np.uint8)
        return cv2.morphologyEx(result, cv2.MORPH_OPEN, kernel)

    @staticmethod
    def _inside_zone(bounds: tuple[int, int, int, int], zone: Dict[str, Any], width: int, height: int) -> bool:
        x1, y1, x2, y2 = bounds
        return (
            x1 >= float(zone["x1"]) * width
            and y1 >= float(zone["y1"]) * height
            and x2 <= float(zone["x2"]) * width
            and y2 <= float(zone["y2"]) * height
        )

    @staticmethod
    def _centre_in_zone(bounds: tuple[int, int, int, int], zone: Dict[str, Any], width: int, height: int) -> bool:
        x1, y1, x2, y2 = bounds
        cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        return (
            float(zone["x1"]) * width <= cx <= float(zone["x2"]) * width
            and float(zone["y1"]) * height <= cy <= float(zone["y2"]) * height
        )

    def _held_seconds(self, name: str, zone_name: str, now: float, max_gap: float) -> float:
        previous = self._hold_state.get(name)
        if previous is None or previous[0] != zone_name or now - previous[2] > max_gap:
            state = (zone_name, now, now, 1)
        else:
            state = (zone_name, previous[1], now, previous[3] + 1)
        self._hold_state[name] = state
        return max(0.0, now - state[1])

    def _detect_payload_transfer(self, frame: np.ndarray, now: float) -> list[Dict[str, Any]]:
        config = self._experiment.get("perception") or {}
        color_config = config.get("color_detection") or {}
        zones = color_config.get("zones") or {}
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        height, width = frame.shape[:2]
        minimum_area = int(color_config.get("min_contour_area", 180))
        minimum_purity = float(color_config.get("min_color_purity", 0.45))
        max_gap = float(color_config.get("min_observation_gap_seconds", 0.5))
        required_hold = float(color_config.get("required_hold_seconds", 1.0))
        red = self._detect_markers(frame, {
            int((config.get("rack_state_markers") or {}).get("rack_opened", -1)): "rack_opened",
            int((config.get("rack_state_markers") or {}).get("rack_closed", -2)): "rack_closed",
        }, str(config.get("aruco_dictionary", "DICT_4X4_50")))
        detections: list[Dict[str, Any]] = list(red)
        boxes: Dict[str, Dict[str, Any]] = {}
        for name, ranges_key, zone_name in (
            ("red_box", "red_hsv_ranges", "zone_a"),
            ("yellow_box", "yellow_hsv_ranges", "zone_b"),
        ):
            mask = self._mask_from_ranges(hsv, color_config.get(ranges_key, []))
            contours, _hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                self._hold_state.pop(name, None)
                continue
            contour = max(contours, key=cv2.contourArea)
            contour_area = float(cv2.contourArea(contour))
            if contour_area < minimum_area:
                self._hold_state.pop(name, None)
                continue
            x, y, box_width, box_height = cv2.boundingRect(contour)
            bounds = (x, y, x + box_width, y + box_height)
            mask_pixels = float(cv2.countNonZero(mask[y:y + box_height, x:x + box_width]))
            purity = mask_pixels / max(1.0, float(box_width * box_height))
            confidence = max(0.0, min(1.0, purity))
            zone = zones.get(zone_name)
            if not isinstance(zone, dict):
                detection = self._box(name, min(confidence, 0.69), bounds, protocol_uncertainty="zone_not_configured")
                boxes[name] = detection
                detections.append(detection)
                continue
            fully_inside = self._inside_zone(bounds, zone, width, height)
            centre_inside = self._centre_in_zone(bounds, zone, width, height)
            other_zone = zones.get("zone_b" if zone_name == "zone_a" else "zone_a", {})
            wrong_zone = bool(other_zone) and self._inside_zone(bounds, other_zone, width, height)
            object_metadata: Dict[str, Any] = {
                "color_purity": round(purity, 3),
                "color_purity_ok": purity >= minimum_purity,
                "confidence_basis": "measured_color_mask_purity",
                "zone": zone_name if fully_inside else ("other_zone" if wrong_zone else None),
                "fully_inside_zone": fully_inside,
                "center_inside_zone": centre_inside,
            }
            if purity < minimum_purity:
                object_metadata["uncertainty_reason"] = "COLOR_SEGMENTATION_AMBIGUOUS"
            elif wrong_zone:
                object_metadata["protocol_violation"] = "WRONG_ZONE"
                object_metadata["guidance"] = f"{name.replace('_', ' ').title()} is in the wrong zone. Move it fully into {zone_name.replace('_', ' ').upper()}."
            elif not fully_inside:
                object_metadata["protocol_violation"] = "BOX_NOT_FULLY_IN_ZONE"
                object_metadata["guidance"] = f"Move the entire {name.replace('_', ' ')} inside {zone_name.replace('_', ' ').upper()}."
            elif fully_inside:
                held = self._held_seconds(name, zone_name, now, max_gap)
                object_metadata["held_seconds"] = round(held, 3)
                object_metadata["required_hold_seconds"] = required_hold
                if held < required_hold:
                    confidence = min(confidence, 0.69)
                    object_metadata["uncertainty_reason"] = "HOLD_NOT_MET"
            else:
                self._hold_state.pop(name, None)
            detection = self._box(name, confidence, bounds, **object_metadata)
            boxes[name] = detection
            detections.append(detection)

        red_box = boxes.get("red_box")
        yellow_box = boxes.get("yellow_box")
        if red_box and yellow_box:
            red_meta = red_box.get("metadata", {})
            yellow_meta = yellow_box.get("metadata", {})
            both_held = (
                red_meta.get("fully_inside_zone")
                and yellow_meta.get("fully_inside_zone")
                and red_meta.get("held_seconds", 0.0) >= required_hold
                and yellow_meta.get("held_seconds", 0.0) >= required_hold
            )
            if both_held:
                r = red_box["bbox"]
                y = yellow_box["bbox"]
                combined_bounds = (
                    min(r["x1"], y["x1"]), min(r["y1"], y["y1"]),
                    max(r["x2"], y["x2"]), max(r["y2"], y["y2"]),
                )
                detections.append(self._box(
                    "both_boxes_verified",
                    min(red_box["confidence"], yellow_box["confidence"]),
                    combined_bounds,
                    zone_a=red_meta.get("zone"),
                    zone_b=yellow_meta.get("zone"),
                    both_visible=True,
                    hold_seconds=required_hold,
                ))
        return detections

    def _detect_plant_markers(self, frame: np.ndarray, now: float) -> list[Dict[str, Any]]:
        config = self._experiment.get("perception") or {}
        marker_map = {int(marker_id): str(object_id) for marker_id, object_id in (config.get("marker_objects") or {}).items()}
        detections = self._detect_markers(frame, marker_map, str(config.get("aruco_dictionary", "DICT_4X4_50")))
        by_id = {detection.get("metadata", {}).get("marker_id"): detection for detection in detections}
        return detections

    def apply_hand_context(
        self,
        detections: list[Dict[str, Any]],
        hands: list[Dict[str, Any]],
        frame_shape: tuple[int, ...],
    ) -> None:
        """Add simulated watering only when a tracked hand engages nearby markers."""
        if str((self._experiment.get("perception") or {}).get("strategy", "")) != "plant_monitoring":
            return
        by_name = {item.get("name"): item for item in detections}
        plant = by_name.get("plant")
        watering_tool = by_name.get("watering_tool")
        if not plant or not watering_tool or not hands:
            return
        height, width = frame_shape[:2]
        scale = float(max(width, height))
        config = self._experiment.get("perception") or {}
        watering = config.get("watering") or {}
        max_marker_distance = float(watering.get("max_marker_distance_normalized", 0.12))
        max_hand_distance = float(watering.get("max_hand_distance_normalized", 0.18))
        plant_center = plant["center"]
        tool_center = watering_tool["center"]
        marker_distance = math.hypot(
            plant_center["x"] - tool_center["x"],
            plant_center["y"] - tool_center["y"],
        ) / scale
        hand_distance = min((
            math.hypot(
                float(hand.get("center", [float("inf"), float("inf")])[0]) - tool_center["x"],
                float(hand.get("center", [float("inf"), float("inf")])[1]) - tool_center["y"],
            ) / scale
            for hand in hands
            if hand.get("center") and len(hand["center"]) >= 2
        ), default=float("inf"))
        if marker_distance > max_marker_distance or hand_distance > max_hand_distance:
            return
        bounds = (
            min(plant["bbox"]["x1"], watering_tool["bbox"]["x1"]),
            min(plant["bbox"]["y1"], watering_tool["bbox"]["y1"]),
            max(plant["bbox"]["x2"], watering_tool["bbox"]["x2"]),
            max(plant["bbox"]["y2"], watering_tool["bbox"]["y2"]),
        )
        hand_confidence = max((float(hand.get("confidence", 0.0)) for hand in hands), default=0.0)
        detections.append(self._box(
            "simulated_watering",
            hand_confidence,
            bounds,
            marker_ids=[11, 12],
            normalized_marker_distance=round(marker_distance, 4),
            normalized_hand_distance=round(hand_distance, 4),
            method="marker_and_hand_proximity_simulation",
            confidence_basis="mediapipe_hand_confidence_with_exact_marker_ids",
            water_quantity_measured=False,
        ))

    def detect(self, frame: np.ndarray) -> list[Dict[str, Any]]:
        self._refresh_protocol()
        result = list(self.base_detector.detect(frame))
        strategy = str((self._experiment.get("perception") or {}).get("strategy", ""))
        now = self._last_detection_timestamp
        if strategy == "payload_transfer":
            result.extend(self._detect_payload_transfer(frame, self._last_detection_timestamp))
        elif strategy == "plant_monitoring":
            result.extend(self._detect_plant_markers(frame, self._last_detection_timestamp))
        return result

    def draw_detections(self, frame: np.ndarray, detections: list[dict[str, Any]]) -> np.ndarray:
        return self.base_detector.draw_detections(frame, detections)

    def get_model_info(self) -> Dict[str, Any]:
        info = self.base_detector.get_model_info() if hasattr(self.base_detector, "get_model_info") else {}
        info["experiment_id"] = self._experiment.get("experiment_id")
        info["perception_strategy"] = (self._experiment.get("perception") or {}).get("strategy", "yolo")
        return info
