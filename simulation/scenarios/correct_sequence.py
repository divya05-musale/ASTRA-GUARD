"""Correct sequence: all 8 steps correct, confidence 0.95."""
from __future__ import annotations

CORRECT = [("CHECK_EQUIPMENT", "experiment_container"), ("RETRIEVE_SAMPLE", "biological_sample"),
           ("OPEN_CONTAINER", "sample_chamber"), ("TRANSFER_SAMPLE", "sample_chamber"),
           ("START_EXPERIMENT", "experiment_controller"), ("RECORD_RESULT", "observation_interface"),
           ("SECURE_SAMPLE", "sample_chamber"), ("COMPLETE_EXPERIMENT", "experiment_controller")]


def build_events(gen, orientation: int = 0):
    gen.reset()
    return [gen.generate_event(activity=a, object=o, confidence=0.95,
                               orientation=orientation, scenario="correct_sequence") for a, o in CORRECT]

