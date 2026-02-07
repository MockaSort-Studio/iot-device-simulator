#!/usr/bin/env python
import logging
import signal
import sys
import threading
import time
from typing import Any, Dict

import config.types as tp
import orjson as json
import schedule
from core.iotunit import IOTUnit
from core.networkclients import NetworkInterface, NetworkInterfaceBuilder


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
            level=logging.DEBUG,
        )
        self.unit_register: Dict[str, IOTUnit]
        self.network_client: NetworkInterface
        self.shutdown_flag: threading.Event
        self.scheduler: schedule.Scheduler
        self.scheduler_thread: threading.Thread

        self.bind_signal_handlers()
        self.setup_daemon_thread()
        self.setup_client(client_cfg)
        self.init_units(units_cfg)

    def load_config(
        self, json_config_file_path: str
    ) -> tuple[tp.LoggerConfig, tp.ClientConfig, tp.UnitsConfig]:
        try:
            with open(json_config_file_path, "rb") as f:
                json_config = json.loads(f.read())
            return tp.parse_config(json_config)
        except Exception:
            raise ProgramKilled

    def bind_signal_handlers(self) -> None:
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, signum: int, frame: Any) -> None:
        self.shutdown_flag.set()
        logging.info("shutdown signal received")
        raise ProgramKilled

    def setup_daemon_thread(self) -> None:
        self.shutdown_flag = threading.Event()
        self.scheduler = schedule.Scheduler()
        self.scheduler_thread = threading.Thread(
            name="scheduler daemon", target=self.daemon_scheduler
        )
        self.scheduler_thread.daemon = True

    def setup_client(self, client_cfg: tp.ClientConfig) -> None:
        try:
            self.network_client = NetworkInterfaceBuilder.build(client_cfg)
        except Exception:
            logging.error("setup network client failed")
            raise ValueError

    def init_units(self, units_cfg: tp.UnitsConfig) -> None:
        self.unit_register: dict[str, IOTUnit] = {}
        try:
            with open(units_cfg.units_list_file_path, "rb") as f:
                units_list_json = json.loads(f.read())
            for unit in units_list_json:
                unit_model = tp.parse_unit_from_json(unit)
                unit_tmp = IOTUnit(unit_model, self.network_client, self.scheduler)
                self.unit_register[unit_model.name] = unit_tmp
        except Exception:
            logging.error("init iot units failed")
            raise ValueError
        logging.info("iot units initialized -> %s", self.unit_register.keys())

    def daemon_scheduler(self) -> None:
        while not self.shutdown_flag.is_set():
            self.scheduler.run_pending()
            time.sleep(0.5)
        logging.info("scheduler daemon clean shutdown")
        self.scheduler.clear()
        logging.info("scheduler stopped")

    def run(self) -> None:
        logging.info("starting container")
        self.scheduler_thread.start()
        self.network_client.start()

    def shutdown(self) -> None:
        logging.info("stopping container")
        self.scheduler_thread.join()
        self.network_client.stop()
