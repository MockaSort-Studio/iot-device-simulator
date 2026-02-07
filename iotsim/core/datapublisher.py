#!/usr/bin/env python
import logging
import threading
from typing import Callable, Type

import orjson as json
import schedule

import iotsim.core.typedefines as types
from iotsim.config.types import PublisherModel


class DataPublisher:
    def __init__(
        self,
        scheduler: schedule.Scheduler,
        publisher_model: PublisherModel,
        # here we want to avoid the circular import, so we use a string literal for the type hint
        owner: Type["iotsim.core.networkclient.Client"],  # noqa: F821
    ) -> None:
        self.owner = owner
        self.register_read_key = publisher_model.read
        self.topic = publisher_model.topic
        self.register_publisher(scheduler, publisher_model)

    def register_publisher(self, scheduler: schedule.Scheduler, model: PublisherModel):
        try:
            if model.type == types.PERIODIC_TYPE and model.cycle_time_ms is not None:
                scheduler.every(int(model.cycle_time_ms / 1000)).seconds.do(
                    self.run_threaded, self.publish
                )
            elif model.type == types.NOTIFICATION_TYPE:
                pass
        except Exception:
            logging.error("register_publisher -> %s failed", model.id)
            raise ValueError
        logging.info(
            "publishing on topic %(topic)s as %(type)s",
            {"topic": self.topic, "type": model.type},
        )

    def run_threaded(self, job_func: Callable) -> None:
        job_thread = threading.Thread(target=job_func)
        job_thread.start()

    def publish(self) -> None:
        payload = self.owner.get_register_value(self.register_read_key)
        self.owner.client.get_client.publish(self.topic, json.dumps(payload))

    def publish_notification(self) -> None:
        notification_thread = threading.Thread(target=self.publish)
        notification_thread.start()
