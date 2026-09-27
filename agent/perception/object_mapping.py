"""
ASTRA-GUARD protocol object mapping.

Phase 7.5.3:
Maps generic YOLO/COCO object names to protocol-specific objects.

This is a deterministic prototype mapping.
A future domain-specific object detection model can replace it.
"""

from __future__ import annotations

from typing import Dict, Optional


OBJECT_MAPPING: Dict[str, str] = {
    # Biological sample
    "bottle": "biological_sample",

    # Sample chamber / container
    "cup": "sample_chamber",
    "bowl": "sample_chamber",

    # Experiment controller
    "cell phone": "experiment_controller",
    "remote": "experiment_controller",

    # Protocol-level aliases
    "biological_sample": "biological_sample",
    "sample_chamber": "sample_chamber",
    "experiment_controller": "experiment_controller",
    "experiment_container": "experiment_container",
    "observation_interface": "observation_interface",
    # Payload Transfer visual detections.
    "rack_opened": "rack_opened",
    "red_box": "red_box",
    "yellow_box": "yellow_box",
    "both_boxes_verified": "both_boxes_verified",
    "rack_closed": "rack_closed",
    "transfer_complete": "transfer_complete",
    # Plant Monitoring marker/action detections.
    "session_started": "session_started",
    "plant_tray": "plant_tray",
    "plant": "plant",
    "watering_tool": "watering_tool",
    "simulated_watering": "simulated_watering",
    "watering_confirmed": "watering_confirmed",
    "evidence_capture": "evidence_capture",
    "observation_saved": "observation_saved",
    "observation_complete": "observation_complete",
}


def get_object_mapping() -> Dict[str, str]:
    """Return a copy of the object mapping."""
    return OBJECT_MAPPING.copy()


def map_detected_object(yolo_name: str) -> Optional[str]:
    """
    Convert a YOLO/COCO object name into an ASTRA-GUARD
    protocol object.
    """

    if not isinstance(yolo_name, str):
        return None

    normalized_name = yolo_name.strip().lower()

    if not normalized_name:
        return None

    return OBJECT_MAPPING.get(normalized_name)