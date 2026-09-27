"""Wrong object at S002, then recovery and completion."""
from __future__ import annotations


def build_events(gen, orientation: int = 0):
    gen.reset()
    evts = []
    evts.append(gen.generate_event(activity="CHECK_EQUIPMENT", object="experiment_container",
                                   confidence=0.95, orientation=orientation, scenario="wrong_object"))
    evts.append(gen.generate_event(activity="RETRIEVE_SAMPLE", object="wrong_sample",
                                   confidence=0.95, orientation=orientation, scenario="wrong_object"))
    rest = [("RETRIEVE_SAMPLE", "biological_sample"), ("OPEN_CONTAINER", "sample_chamber"),
            ("TRANSFER_SAMPLE", "sample_chamber"), ("START_EXPERIMENT", "experiment_controller"),
            ("RECORD_RESULT", "observation_interface"), ("SECURE_SAMPLE", "sample_chamber"),
            ("COMPLETE_EXPERIMENT", "experiment_controller")]
    for a, o in rest:
        evts.append(gen.generate_event(activity=a, object=o, confidence=0.95,
                                       orientation=orientation, scenario="wrong_object"))
    return evts

