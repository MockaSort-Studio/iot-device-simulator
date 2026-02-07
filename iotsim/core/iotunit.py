#!/usr/bin/env python
import importlib
import logging
from typing import Dict

from apscheduler.schedulers.background import BackgroundScheduler
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
        scheduler: BackgroundScheduler,
    ) -> None:
        self.client = client  # to be improved with complete refactoring
        self.name = unit_model.name
        self.state_registry = StateRegistry(unit_model.registers)
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
        self, scheduler: BackgroundScheduler, model: UnitModel
    ) -> None:
        try:
            sleep_time = model.control_loop_sleep_ms / 1000
            control_loop_module = importlib.import_module(model.control_loop_module)
            scheduler.add_job(
                control_loop_module.run,
                "interval",
                seconds=sleep_time,
                args=[self.state_registry],
                coalesce=False,
                max_instances=1,
            )

            logging.info(
                "control loop %(loop)s initialized for unit %(name)s",
                {"loop": control_loop_module, "name": self.name},
            )
        except Exception:
            logging.error("failed to initialize control loop for unit %s", self.name)
            raise ValueError

    def init_data_publishers(
        self, scheduler: BackgroundScheduler, pubList: list[PublisherModel]
    ) -> None:
        for pub in pubList:
            pub_tmp = DataPublisher(pub, self.client, self.state_registry)
            scheduler.add_job(
                pub_tmp.publish,
                "interval",
                seconds=pub_tmp.publish_frequency_ms / 1000,
                coalesce=False,
                # args=[pub_tmp],  # self
                max_instances=1,
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
