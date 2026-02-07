import logging

from config.types import SubscriberModel
from core.networkclients import NetworkInterface
from core.stateregistry import StateRegistry


class DataSubscriber:
    def __init__(
        self,
        subscriber_model: SubscriberModel,
        network_client: NetworkInterface,
        data_registry: StateRegistry,
    ) -> None:
        self.topic = subscriber_model.topic
        self.register_write_key = subscriber_model.write
        self.network_client = network_client
        self.data_registry = data_registry

        self._init_subscriber(subscriber_model)

    def _init_subscriber(self, model: SubscriberModel) -> None:
        self.network_client.subscribe(self.topic, self.on_message_data_write)
        logging.info(
            "subscribed topic %(topic)s for writing to register %(register)s",
            {"topic": self.topic, "register": self.register_write_key},
        )

    def on_message_data_write(self, message: str) -> None:
        self.data_registry.update(self.register_write_key, str(message))
