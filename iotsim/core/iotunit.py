#!/usr/bin/env python
import importlib
import logging
import threading

import iotsim.core.typedefines as types
from iotsim.core.datapublisher import DataPublisher
from iotsim.core.datasubscriber import DataSubscriber


class IOTUnit:
    def __init__(self) -> None:
        pass

    def __init__(self, unit_cfg, client, scheduler):
        self.client = client  # to be improved with complete refactoring
        self.name = unit_cfg["name"]
        self.registers = unit_cfg["registers"]
        self.notifiers = {}
        self.publishers = {}
        self.subscribers = {}
        self.init_data_publishers(
            scheduler, unit_cfg["publishers"]
        )  # step 2 -> init data publisher
        if "subscribers" in unit_cfg:  # step 3 -> init data subscriber
            self.init_data_subscribers(
                unit_cfg["subscribers"]
            )  # step 4 -> init control loop
        self.init_control_loop(scheduler, unit_cfg)

    def init_control_loop(self, scheduler, cfg):
        try:
            control_loop_module = cfg["control_loop_module"]
            if control_loop_module is None:
                pass
            else:
                sleep_time = cfg["control_loop_sleep_ms"]
                self.control_loop_module = importlib.import_module(control_loop_module)
                scheduler.every(sleep_time / 1000).seconds.do(
                    self.control_loop_threaded, self.control_loop_module.run
                )
                logging.info(
                    "control loop %(loop)s initialized for unit %(name)s",
                    {"loop": control_loop_module, "name": self.name},
                )
        except Exception:
            logging.error("failed to initialize control loop for unit %s", self.name)
            raise ValueError

    def init_data_publishers(self, scheduler, pubList):
        try:
            for pub in pubList:
                pub_tmp = DataPublisher(scheduler, pub, self)
                if pub["type"] == types.NOTIFICATION_TYPE:
                    self.notifiers[pub["id"]] = pub_tmp
                else:
                    self.publishers[pub["id"]] = pub_tmp
        except Exception:
            logging.error("init data publishers failed for unit %s", self.name)
            raise ValueError
        logging.debug(
            "init data publisher -notifiers:%(notifiers)s -publishers:%(publishers)s",
            {"notifiers": self.notifiers, "publishers": self.publishers},
        )

    def init_data_subscribers(self, subList):
        try:
            for sub in subList:
                sub_tmp = DataSubscriber(sub, self)
                self.subscribers[sub["id"]] = sub_tmp
        except Exception:
            logging.error("init data subscribers failed for unit %s", self.name)
            raise ValueError
        logging.debug("init data subscribers -subscribers:%s", self.subscribers)

    def get_register_value(self, key):
        return self.registers[key]

    def set_register_value(self, key, value):
        logging.debug(
            "setting register %(key)s -> old value:%(oldV)s new value:%(newV)s",
            {"key": key, "oldV": self.registers[key], "newV": value},
        )
        self.registers[key] = value

    def control_loop_threaded(self, job_func):
        job_thread = threading.Thread(target=job_func, args=(self.registers,))
        job_thread.start()

    def process_request_threaded(self, req_func, payload, notifier_name_key):
        req_thread = threading.Thread(
            target=req_func,
            args=(
                self.registers,
                payload,
                self.notifiers[notifier_name_key].publish_notification,
            ),
        )
        req_thread.start()
