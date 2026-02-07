#!/usr/bin/env python
import importlib
import logging
import threading
from typing import Any, Callable, Dict

import schedule

import iotsim.core.typedefines as types
from iotsim.config.types import PublisherModel, SubscriberModel, UnitModel
from iotsim.core.datapublisher import DataPublisher
from iotsim.core.datasubscriber import DataSubscriber
from iotsim.core.networkclients import Client


class IOTUnit:
    def __init__(
        self, unit_model: UnitModel, client: Client, scheduler: schedule.Scheduler
    ) -> None:
        self.client = client  # to be improved with complete refactoring
        self.name = unit_model.name
        self.registers = unit_model.registers
        self.notifiers: Dict[str, DataPublisher] = {}
        self.publishers: Dict[str, DataPublisher] = {}
        self.subscribers: Dict[str, DataSubscriber] = {}
        self.init_data_publishers(
            scheduler, unit_model.publishers
        )  # step 2 -> init data publisher
        self.init_data_subscribers(
            unit_model.subscribers
        )  # step 4 -> init control loop
        self.init_control_loop(scheduler, unit_model)

    def init_control_loop(
        self, scheduler: schedule.Scheduler, model: UnitModel
    ) -> None:
        try:
            if model.control_loop_module is None or model.control_loop_sleep_ms is None:
                pass
            else:
                # TODO this could be improved by increasing granularity in the sleep time that would mean change scheduling method
                sleep_time = int(model.control_loop_sleep_ms / 1000)
                control_loop_module = importlib.import_module(model.control_loop_module)
                scheduler.every(sleep_time).seconds.do(
                    self.control_loop_threaded, control_loop_module.run
                )
                logging.info(
                    "control loop %(loop)s initialized for unit %(name)s",
                    {"loop": control_loop_module, "name": self.name},
                )
        except Exception:
            logging.error("failed to initialize control loop for unit %s", self.name)
            raise ValueError

    def init_data_publishers(
        self, scheduler: schedule.Scheduler, pubList: list[PublisherModel]
    ) -> None:
        try:
            for pub in pubList:
                pub_tmp = DataPublisher(scheduler, pub, self)
                if pub.type == types.NOTIFICATION_TYPE:
                    self.notifiers[pub.id] = pub_tmp
                else:
                    self.publishers[pub.id] = pub_tmp
        except Exception:
            logging.error("init data publishers failed for unit %s", self.name)
            raise ValueError
        logging.debug(
            "init data publisher -notifiers:%(notifiers)s -publishers:%(publishers)s",
            {
                "notifiers": list(self.notifiers.keys()),
                "publishers": list(self.publishers.keys()),
            },
        )

    def init_data_subscribers(self, subList: list[SubscriberModel]) -> None:
        try:
            for sub in subList:
                sub_tmp = DataSubscriber(sub, self)
                self.subscribers[sub.id] = sub_tmp
        except Exception:
            logging.error("init data subscribers failed for unit %s", self.name)
            raise ValueError
        logging.debug(
            "init data subscribers -subscribers:%s", list(self.subscribers.keys())
        )

    def get_register_value(self, key: str) -> Any:
        return self.registers[key]

    def set_register_value(self, key: str, value: Any) -> None:
        logging.debug(
            "setting register %(key)s -> old value:%(oldV)s new value:%(newV)s",
            {"key": key, "oldV": self.registers[key], "newV": value},
        )
        self.registers[key] = value

    def control_loop_threaded(self, job_func: Callable) -> None:
        job_thread = threading.Thread(target=job_func, args=(self.registers,))
        job_thread.start()

    def process_request_threaded(
        self, req_func: Callable, payload: Any, notifier_name_key: str
    ) -> None:
        req_thread = threading.Thread(
            target=req_func,
            args=(
                self.registers,
                payload,
                self.notifiers[notifier_name_key].publish_notification,
            ),
        )
        req_thread.start()
