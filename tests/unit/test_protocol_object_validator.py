from agent.mission.protocol_object_validator import (
    ProtocolObjectValidator,
)


def make_objects():
    return [
        {
            "object_id": "experiment_container",
            "name": "Experiment Container",
        },
        {
            "object_id": "biological_sample",
            "name": "Biological Sample",
        },
        {
            "object_id": "sample_chamber",
            "name": "Sample Chamber",
        },
        {
            "object_id": "experiment_controller",
            "name": "Experiment Controller",
        },
        {
            "object_id": "observation_interface",
            "name": "Observation Interface",
        },
    ]


def test_known_object_is_valid():
    validator = ProtocolObjectValidator(make_objects())

    assert validator.is_valid("biological_sample")


def test_unknown_object_is_invalid():
    validator = ProtocolObjectValidator(make_objects())

    assert not validator.is_valid("laptop")


def test_none_object_is_invalid():
    validator = ProtocolObjectValidator(make_objects())

    assert not validator.is_valid(None)


def test_get_object_returns_definition():
    validator = ProtocolObjectValidator(make_objects())

    result = validator.get_object("sample_chamber")

    assert result is not None
    assert result["name"] == "Sample Chamber"


def test_unknown_object_returns_none():
    validator = ProtocolObjectValidator(make_objects())

    assert validator.get_object("laptop") is None


def test_all_protocol_objects_are_available():
    validator = ProtocolObjectValidator(make_objects())

    assert len(validator.get_object_ids()) == 5


def test_object_definition_is_returned_as_copy():
    validator = ProtocolObjectValidator(make_objects())

    result = validator.get_object("biological_sample")
    result["name"] = "Changed"

    original = validator.get_object("biological_sample")

    assert original["name"] == "Biological Sample"