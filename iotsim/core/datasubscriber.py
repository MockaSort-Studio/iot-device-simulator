import logging
from typing import Any

from config.types import SubscriberModel
from core.stateregistry import StateRegistry
from paho.mqtt.client import Client, MQTTMessage


# Abstraction of client/visitors can definitely be improved
class DataSubscriber:
    def __init__(
        self,
        subscriber_model: SubscriberModel,
        network_client: Client,
        data_registry: StateRegistry,
    ) -> None:
        self.topic = subscriber_model.topic
        self.register_write_key = subscriber_model.write
        self.network_client = network_client
        self.data_registry = data_registry

        self.register_subscriber(subscriber_model)

    def register_subscriber(self, model: SubscriberModel) -> None:
        self.network_client.subscribe(self.topic, self.on_message_data_write)
        logging.info(
            "subscribed topic %(topic)s for writing to register %(register)s",
            {"topic": self.topic, "register": self.register_write_key},
        )

    def on_message_data_write(
        self, client: Client, userdata: Any, message: MQTTMessage
    ) -> None:
        logging.debug(
            "received %(payload)s on topic %(topic)s",
            {"payload": message.payload, "topic": message.topic},
        )
        self.data_registry.set_value(
            self.register_write_key, str(message.payload.decode("utf-8"))
        )
