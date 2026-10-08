from agent.mission.activity_interpreter import ActivityInterpreter


def test_s001_maps_to_check_equipment():
    interpreter = ActivityInterpreter()

    result = interpreter.interpret(
        step_id="S001",
        detected_object="experiment_container",
        hand_interaction=False,
        confidence=0.90,
    )

    assert result["activity"] == "CHECK_EQUIPMENT"
    assert result["confidence"] > 0.0


def test_s002_maps_to_retrieve_sample():
    interpreter = ActivityInterpreter()

    result = interpreter.interpret(
        step_id="S002",
        detected_object="biological_sample",
        hand_interaction=True,
        confidence=0.90,
    )

    assert result["activity"] == "RETRIEVE_SAMPLE"


def test_s005_maps_to_start_experiment():
    interpreter = ActivityInterpreter()

    result = interpreter.interpret(
        step_id="S005",
        detected_object="experiment_controller",
        hand_interaction=True,
        confidence=0.90,
    )

    assert result["activity"] == "START_EXPERIMENT"


def test_custom_protocol_step_mapping_is_supported():
    interpreter = ActivityInterpreter({"P001": "OPEN_RACK"})

    result = interpreter.interpret(
        step_id="P001",
        detected_object="rack_open_marker",
        hand_interaction=True,
        confidence=0.95,
    )

    assert result["activity"] == "OPEN_RACK"


def test_unknown_step_returns_unknown():
    interpreter = ActivityInterpreter()

    result = interpreter.interpret(
        step_id="S999",
        detected_object="sample_chamber",
        hand_interaction=True,
        confidence=0.90,
    )

    assert result["activity"] == "UNKNOWN_STEP"


def test_missing_object_returns_unknown():
    interpreter = ActivityInterpreter()

    result = interpreter.interpret(
        step_id="S002",
        detected_object=None,
        hand_interaction=True,
        confidence=0.90,
    )

    assert result["activity"] == "NO_OBJECT"