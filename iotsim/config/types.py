from typing import Any, Dict

from pydantic import BaseModel, Field


class LoggerConfig(BaseModel):
    file_path: str = Field(..., description="Logger File Path")
    verbosity: str = Field(..., description="Logger Verbosity")


class ClientConfig(BaseModel):
    id: str = Field(..., description="Client ID")
    type: str = Field(
        default="mqtt", description="Protocol Type: currently supports: mqtt"
    )
    host: str = Field(..., description="Client Host")
    port: int = Field(..., description="Client Port")
    root_ca_path: str = Field(..., description="Client Root CA Path")
    client_certificate_path: str = Field(..., description="Client Certificate Path")
    client_key_path: str = Field(..., description="Client Private Key Path")


class UnitsConfig(BaseModel):
    units_list_file_path: str = Field(..., description="IoTUnits List File Path")
    units_py_module_path: str = Field(
        ..., description="Path to folder containing units logic implementations"
    )


def parse_config(
    json_dict: Dict[str, Any],
) -> tuple[LoggerConfig, ClientConfig, UnitsConfig]:
    try:
        logger_cfg = LoggerConfig(**json_dict["logger"])
        client_cfg = ClientConfig(**json_dict["client"])
        units_cfg = UnitsConfig(**json_dict["units"])
        return logger_cfg, client_cfg, units_cfg
    except KeyError as e:
        raise ValueError(f"Missing required config section: {e}")


class PublisherModel(BaseModel):
    id: str = Field(..., description="Publisher ID")
    type: str = Field(..., description="Publisher Type: NOTIFICATION or PERIODIC")
    topic: str = Field(..., description="Topic to publish to")
    read: str = Field(..., description="Key of the register to read data from")
    cycle_time_ms: int | None = Field(
        default=None,
        description="Publishing interval in milliseconds (only for PERIODIC publishers)",
    )


class SubscriberModel(BaseModel):
    id: str = Field(..., description="Subscriber ID")
    type: str = Field(..., description="Subscriber Type: REQUEST or DATA_WRITE")
    topic: str = Field(..., description="Topic to subscribe to")
    write: str = Field(..., description="Key of the register to write data to")
    request_module: str | None = Field(
        default=None,
        description="Path to module containing request handling logic (only for REQUEST subscribers)",
    )
    notifier: str | None = Field(
        default=None,
        description="ID of the NOTIFICATION publisher to trigger after handling the request (only for REQUEST subscribers)",
    )


class UnitModel(BaseModel):
    name: str = Field(..., description="Unit Name")
    registers: Dict[str, Any] = Field(..., description="Unit Registers")
    publishers: list[PublisherModel] = Field(
        ..., description="List of Unit Data Publishers"
    )
    subscribers: list[SubscriberModel] = Field(
        default_factory=list, description="List of Unit Data Subscribers"
    )
    control_loop_module: str | None = Field(
        default=None,
        description="Path to module containing control loop logic (optional)",
    )
    control_loop_sleep_ms: int | None = Field(
        default=None,
        description="Sleep time in milliseconds for control loop execution (optional)",
    )


def parse_unit_from_json(json_dict: Dict[str, Any]) -> UnitModel:
    try:
        return UnitModel(**json_dict)
    except KeyError as e:
        raise ValueError(f"Missing required unit config field: {e}")
