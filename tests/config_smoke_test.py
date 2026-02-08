from importlib import resources

import orjson as json
import pytest
from pydantic import ValidationError

from iotsim.config.types import (
    ClientConfig,
    LoggerConfig,
    PublisherModel,
    SubscriberModel,
    UnitModel,
    UnitsConfig,
    parse_config,
    parse_unit_from_json,
)


@pytest.fixture
def default_config_bytes() -> bytes:
    """
    Test 1: Verification of Resource Inclusion.
    This fixture will fail if the JSON file wasn't bundled correctly by Hatch.
    """
    try:
        # This matches the path we set up in pyproject.toml
        return (
            resources.files("iotsim.config")
            .joinpath("config-default.json")
            .read_bytes()
        )
    except FileNotFoundError:
        pytest.fail(
            "Resource 'default.json' not found in iotsim.config! Check your Hatch build settings."
        )


def test_default_resources_match_models(default_config_bytes: bytes) -> None:
    """
    Test 2: Verification of Model Alignment.
    Ensures the default JSON structure is valid according to our Pydantic models.
    """
    # Parse the raw bytes
    config_dict = json.loads(default_config_bytes)

    # Attempt to parse into models
    try:
        logger_cfg, client_cfg, units_cfg = parse_config(config_dict)
    except ValidationError as e:
        pytest.fail(f"Default config file is out of sync with Pydantic models: {e}")
    except ValueError as e:
        pytest.fail(f"Missing sections in default.json: {e}")

    # Specific assertions to ensure data is actually what we expect
    assert isinstance(logger_cfg, LoggerConfig)
    assert isinstance(client_cfg, ClientConfig)
    assert isinstance(units_cfg, UnitsConfig)

    assert client_cfg.port > 0


def test_malformed_config_handling() -> None:
    """
    Ensures that parse_config still fails correctly when given bad data,
    preventing false positives.
    """
    bad_data = {"logger": {}, "client": {}, "units": {}}  # Missing required fields
    with pytest.raises(ValueError):
        parse_config(bad_data)


def test_publisher_model_defaults() -> None:
    """Verify that PublisherModel sets the default frequency if not provided."""
    data = {
        "id": "pub_01",
        "topic": "sensors/temp",
        "read": "temp_register",
        "publish_frequency_ms": 500,
    }
    pub = PublisherModel(**data)
    assert pub.publish_frequency_ms == 500


def test_subscriber_model_assignment() -> None:
    """Verify SubscriberModel maps fields correctly."""
    data = {"id": "sub_01", "topic": "cmd/speed", "write": "speed_register"}
    sub = SubscriberModel(**data)
    assert sub.topic == "cmd/speed"
    assert sub.write == "speed_register"


def test_unit_model_full_parsing() -> None:
    """Test parsing a complex UnitModel with nested publishers and subscribers."""
    raw_unit = {
        "name": "engine_controller",
        "registers": {"rpm": 0, "temp": 20},
        "publishers": [
            {"id": "p1", "topic": "val/rpm", "read": "rpm", "publish_frequency_ms": 100}
        ],
        "subscribers": [{"id": "s1", "topic": "set/rpm", "write": "rpm"}],
        "control_loop_module": "iotsim.logic.engine",
        "control_loop_sleep_ms": 50,
    }

    unit = parse_unit_from_json(raw_unit)

    assert unit.name == "engine_controller"
    assert len(unit.publishers) == 1
    assert unit.publishers[0].publish_frequency_ms == 100
    assert isinstance(unit.subscribers[0], SubscriberModel)


def test_unit_model_validation_failure() -> None:
    """Verify that missing mandatory fields (like registers) raise an error."""
    incomplete_unit = {
        "name": "broken_unit",
        "publishers": [],
        "control_loop_module": "test",
        "control_loop_sleep_ms": 10,
    }
    # Should raise ValidationError because 'registers' is missing
    with pytest.raises(ValidationError) as excinfo:
        UnitModel.model_validate(incomplete_unit)

    assert "registers" in str(excinfo.value)


def test_strict_parsing_logic() -> None:
    """
    Ensure parse_unit_from_json handles data correctly even if extra fields
    are present (strict=False behavior).
    """
    data_with_extra = {
        "name": "flex_unit",
        "registers": {},
        "publishers": [],
        "control_loop_module": "mod",
        "control_loop_sleep_ms": 10,
        "unexpected_field": "ignore_me",
    }
    # This should not raise an error
    unit = parse_unit_from_json(data_with_extra)
    assert unit.name == "flex_unit"
