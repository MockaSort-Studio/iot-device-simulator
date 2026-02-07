import logging
from typing import Any, Callable

from config.types import SubscriberModel
from paho.mqtt.client import Client, MQTTMessage


# Abstraction of client/visitors can definitely be improved
class DataSubscriber:
    def __init__(
        self,
        subscriber_model: SubscriberModel,
        network_client: Client,
        set_register_value: Callable[[str, str], None],
        # here we want to avoid the circular import, so we use a string literal for the type hint
    ) -> None:
        self.topic = subscriber_model.topic
        self.register_write_key = subscriber_model.write
        self.network_client = network_client
        self.set_register_value = set_register_value

        self.register_subscriber(subscriber_model)

    def register_subscriber(self, model: SubscriberModel) -> None:
        self.network_client.subscribe(self.topic)
        self.network_client.message_callback_add(self.topic, self.on_message_data_write)
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
        self.set_register_value(
            self.register_write_key, str(message.payload.decode("utf-8"))
        )
