#!/usr/bin/env python
import importlib
import logging
import threading
from typing import Any, Callable, Dict

import schedule
from config.types import PublisherModel, SubscriberModel, UnitModel
from core.datapublisher import DataPublisher
from core.datasubscriber import DataSubscriber
from core.networkclients import NetworkInterface
from core.stateregistry import StateRegistry


class IOTUnit:
    def __init__(
        self,
        unit_model: UnitModel,
        client: NetworkInterface,
        scheduler: schedule.Scheduler,
    ) -> None:
        self.client = client  # to be improved with complete refactoring
        self.name = unit_model.name
        self.registers = unit_model.registers
        self.state_registry = StateRegistry(self.registers)
        self.publishers: Dict[str, DataPublisher] = {}
        self.subscribers: Dict[str, DataSubscriber] = {}

        self.init_data_publishers(
            scheduler, unit_model.publishers
        )  # step 2 -> init data publisher
        self.init_data_subscribers(
            unit_model.subscribers
        )  # step 4 -> init control loop
        self.init_control_loop(scheduler, unit_model)

    def _control_loop_internal(self, control_loop_func: Callable) -> None:
        control_loop_func(self.registers)

    def init_control_loop(
        self, scheduler: schedule.Scheduler, model: UnitModel
    ) -> None:
        try:
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
        for pub in pubList:
            pub_tmp = DataPublisher(
                scheduler, pub, self.client.publish, self.state_registry
            )
            self.publishers[pub.id] = pub_tmp
        logging.debug(
            "init data publishers:%(publishers)s",
            {
                "publishers": list(self.publishers.keys()),
            },
        )

    def init_data_subscribers(self, subList: list[SubscriberModel]) -> None:
        for sub in subList:
            sub_tmp = DataSubscriber(sub, self.client, self.state_registry)
            self.subscribers[sub.id] = sub_tmp
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
