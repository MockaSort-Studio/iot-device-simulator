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
