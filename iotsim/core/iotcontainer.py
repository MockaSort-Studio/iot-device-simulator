#!/usr/bin/env python
import logging
import os
import signal
import sys
import threading
from datetime import timezone
from importlib import resources
from typing import Any, Dict

import orjson as json
from apscheduler.schedulers.background import BackgroundScheduler

import iotsim.config.types as tp
from iotsim.core.iotunit import IOTUnit
from iotsim.core.networkclients import NetworkInterface, NetworkInterfaceBuilder


class ProgramKilled(Exception):
    pass


class IOTContainer:
    def __init__(self, json_config_file_path: str) -> None:
        logger_cfg, client_cfg, units_cfg = self.load_config(json_config_file_path)
        sys.path.append(units_cfg.units_py_module_path)
        logging.basicConfig(
            filename=logger_cfg.file_path,
            filemode="w",
            format="%(asctime)s -%(levelname)s- %(message)s",
            level=logger_cfg.verbosity,
        )
        self.unit_register: Dict[str, IOTUnit]
        self.network_client: NetworkInterface
        self.scheduler = BackgroundScheduler(timezone=timezone.utc)
        self.shutdown_flag: threading.Event = threading.Event()
        self.bind_signal_handlers()
        self.setup_client(client_cfg)
        self.init_units(units_cfg)

    def load_config(
        self, json_config_file_path: str
    ) -> tuple[tp.LoggerConfig, tp.ClientConfig, tp.UnitsConfig]:
        try:
            if not json_config_file_path:
                # Load from package resources if path is empty
                logging.info("No config path provided, loading default from resources.")
                config_resource = resources.files("iotsim.config").joinpath(
                    "config-default.json"
                )
                config_bytes = config_resource.read_bytes()
                json_config = json.loads(config_bytes)
            else:
                # Load from the provided filesystem path
                with open(json_config_file_path, "rb") as f:
                    json_config = json.loads(f.read())

            return tp.parse_config(json_config)

        except FileNotFoundError as e:
            logging.error("Configuration file not found: %s", e)
            raise ProgramKilled from e
        except Exception as e:
            logging.error("Failed to load config: %s", e)
            raise ProgramKilled from e

    def bind_signal_handlers(self) -> None:
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, _: int, frame: Any) -> None:
        self.shutdown_flag.set()
        logging.info("shutdown signal received")
        raise ProgramKilled

    def setup_client(self, client_cfg: tp.ClientConfig) -> None:
        try:
            self.network_client = NetworkInterfaceBuilder.build(client_cfg)
        except Exception as e:
            logging.error("setup network client failed: %s", str(e))
            raise ValueError

    def init_units(self, units_cfg: tp.UnitsConfig) -> None:
        self.unit_register: dict[str, IOTUnit] = {}
        module_dir: str
        units_list_json: list[dict[str, Any]]
        try:
            if not units_cfg.units_list_file_path or not units_cfg.units_py_module_path:
                logging.info(
                    "Units list or Module path is blank; falling back to internal examples."
                )
                res_path = resources.files("iotsim.examples").joinpath("iotunits.json")
                units_list_json = json.loads(res_path.read_bytes())
                module_dir = str(resources.files("iotsim.examples"))
            else:
                with open(units_cfg.units_list_file_path, "rb") as f:
                    units_list_json = json.loads(f.read())
                    module_dir = os.path.abspath(units_cfg.units_py_module_path)

            # 3. Add to sys.path and initialize
            if module_dir not in sys.path:
                sys.path.append(module_dir)

            for unit in units_list_json:
                unit_model = tp.parse_unit_from_json(unit)
                unit_tmp = IOTUnit(unit_model, self.network_client, self.scheduler)
                self.unit_register[unit_model.name] = unit_tmp
        except Exception as e:
            logging.error("init iot units failed: %s", e)
            raise ValueError(f"Failed to initialize units: {e}") from e

    def run(self) -> None:
        logging.info(
            "Starting IOT Container - this call starts background threads, be sure to block execution afterwards"
        )
        self.network_client.start()
        self.scheduler.start()

    def shutdown(self) -> None:
        logging.info("Shutting down...")
        self.scheduler.shutdown(wait=True)
        self.network_client.stop()
        logging.info("Container stopped.")
