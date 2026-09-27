from agent.perception.object_mapping import (
    get_object_mapping,
    map_detected_object,
)


def test_bottle_maps_to_biological_sample():
    assert map_detected_object("bottle") == "biological_sample"


def test_cup_maps_to_sample_chamber():
    assert map_detected_object("cup") == "sample_chamber"


def test_cell_phone_maps_to_experiment_controller():
    assert map_detected_object("cell phone") == "experiment_controller"


def test_bowl_maps_to_sample_chamber():
    assert map_detected_object("bowl") == "sample_chamber"


def test_remote_maps_to_experiment_controller():
    assert map_detected_object("remote") == "experiment_controller"


def test_protocol_object_alias_is_supported():
    assert map_detected_object("biological_sample") == "biological_sample"


def test_unknown_object_returns_none():
    assert map_detected_object("laptop") is None


def test_empty_object_returns_none():
    assert map_detected_object("") is None


def test_mapping_returns_copy():
    mapping = get_object_mapping()

    mapping["test"] = "something"

    assert "test" not in get_object_mapping()