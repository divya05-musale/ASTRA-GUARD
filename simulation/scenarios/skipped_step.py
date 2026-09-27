"""Skipped step: attempt S004 activity while S002 expected (gap > 1)."""
def build_events(gen, orientation: int = 0):
    gen.reset()
    evts = [gen.generate_event(activity="CHECK_EQUIPMENT", object="experiment_container",
                               confidence=0.95, orientation=orientation, scenario="skipped_step")]
    evts.append(gen.generate_event(activity="TRANSFER_SAMPLE", object="sample_chamber",
                                   confidence=0.95, orientation=orientation, scenario="skipped_step",
                                   notes="synthetic skipped step: S004 attempted while at S002"))
    for a, o in [("RETRIEVE_SAMPLE", "biological_sample"), ("OPEN_CONTAINER", "sample_chamber"),
                 ("TRANSFER_SAMPLE", "sample_chamber"), ("START_EXPERIMENT", "experiment_controller"),
                 ("RECORD_RESULT", "observation_interface"), ("SECURE_SAMPLE", "sample_chamber"),
                 ("COMPLETE_EXPERIMENT", "experiment_controller")]:
        evts.append(gen.generate_event(activity=a, object=o, confidence=0.95,
                                       orientation=orientation, scenario="skipped_step"))
    return evts

