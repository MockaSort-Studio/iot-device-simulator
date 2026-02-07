#!/usr/bin/env python
import logging
import threading
from typing import ByteString, Callable

import orjson as json
import schedule
from config.types import PublisherModel
from core.stateregistry import StateRegistry


class DataPublisher:
    def __init__(
        self,
        scheduler: schedule.Scheduler,
        publisher_model: PublisherModel,
        client_publish: Callable[[str, ByteString], None],
        data_registry: StateRegistry,
        # here we want to avoid the circular import, so we use a string literal for the type hint
    ) -> None:
        self.register_read_key = publisher_model.read
        self.topic = publisher_model.topic
        self.register_publisher(scheduler, publisher_model)
        self.data_registry = data_registry
        self.client_publish = client_publish

    def register_publisher(self, scheduler: schedule.Scheduler, model: PublisherModel):
        scheduler.every(int(model.cycle_time_ms / 1000)).seconds.do(
            self.run_threaded, self.publish
        )
        logging.info(
            "publishing on topic %(topic)s every %(cycle_time)s ms",
            {"topic": self.topic, "cycle_time": model.cycle_time_ms},
        )

    def run_threaded(self, job_func: Callable) -> None:
        job_thread = threading.Thread(target=job_func)
        job_thread.start()

    def publish(self) -> None:
        payload = self.data_registry.get_value(self.register_read_key)
        self.client_publish(self.topic, json.dumps(payload))
