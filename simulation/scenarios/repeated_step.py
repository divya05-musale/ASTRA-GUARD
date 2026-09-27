"""Repeated step: repeat S001 while S002 expected."""
def build_events(gen, orientation: int = 0):
    gen.reset()
    evts = [gen.generate_event(activity="CHECK_EQUIPMENT", object="experiment_container",
                               confidence=0.95, orientation=orientation, scenario="repeated_step")]
    evts.append(gen.generate_event(activity="CHECK_EQUIPMENT", object="experiment_container",
                                   confidence=0.95, orientation=orientation, scenario="repeated_step"))
    for a, o in [("RETRIEVE_SAMPLE", "biological_sample"), ("OPEN_CONTAINER", "sample_chamber"),
                 ("TRANSFER_SAMPLE", "sample_chamber"), ("START_EXPERIMENT", "experiment_controller"),
                 ("RECORD_RESULT", "observation_interface"), ("SECURE_SAMPLE", "sample_chamber"),
                 ("COMPLETE_EXPERIMENT", "experiment_controller")]:
        evts.append(gen.generate_event(activity=a, object=o, confidence=0.95,
                                       orientation=orientation, scenario="repeated_step"))
    return evts

