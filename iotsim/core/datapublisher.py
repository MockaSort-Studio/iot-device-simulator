#!/usr/bin/env python

import orjson as json

from iotsim.config.types import PublisherModel
from iotsim.core.networkclients import NetworkInterface
from iotsim.core.stateregistry import StateRegistry


class DataPublisher:
    def __init__(
        self,
        publisher_model: PublisherModel,
        client: NetworkInterface,
        data_registry: StateRegistry,
    ) -> None:
        self.register_read_key = publisher_model.read
        self.topic = publisher_model.topic
        self.data_registry = data_registry
        self.publish_frequency_ms = publisher_model.publish_frequency_ms
        self.client = client

    def publish(self) -> None:
        payload = self.data_registry.get_value(self.register_read_key)
        self.client.publish(self.topic, json.dumps(payload))
