import importlib
import logging
from typing import Any

from paho.mqtt.client import Client, MQTTMessage

import iotsim.core.typedefines as types
from iotsim.config.types import SubscriberModel


# Abstraction of client/visitors can definetely be improved
class DataSubscriber:
    def __init__(
        self,
        subscriber_model: SubscriberModel,
        # here we want to avoid the circular import, so we use a string literal for the type hint
        owner: "iotsim.core.networkclient.Client",  # noqa: F821
    ) -> None:
        self.owner = owner
        self.topic = subscriber_model.topic
        self.register_subscriber(subscriber_model)

    def register_subscriber(self, model: SubscriberModel) -> None:
        try:
            self.owner.client.get_client.subscribe(self.topic)
            if model.type == types.DATA_WRITE_TYPE:
                self.register_write_key = model.write
                self.owner.client.get_client.message_callback_add(
                    self.topic, self.on_message_data_write
                )
            elif model.type == types.REQUEST_TYPE and model.request_module is not None:
                self.module = importlib.import_module(model.request_module)
                self.notifier_name = model.notifier
                self.owner.client.get_client.message_callback_add(
                    self.topic, self.on_message_request
                )
        except Exception:
            logging.error("register_subscriber -> %s failed", model.id)
            raise ValueError
        logging.info(
            "subscribed topic %(topic)s as %(type)s",
            {"topic": self.topic, "type": model.type},
        )

    def on_message_data_write(
        self, client: Client, userdata: Any, message: MQTTMessage
    ) -> None:
        logging.debug(
            "received %(payload)s on topic %(topic)s",
            {"payload": message.payload, "topic": message.topic},
        )
        self.owner.set_register_value(
            self.register_write_key, str(message.payload.decode("utf-8"))
        )

    def on_message_request(
        self, client: Client, userdata: Any, message: MQTTMessage
    ) -> None:
        logging.debug(
            "request %(payload)s received on topic %(topic)s",
            {"payload": message.payload, "topic": message.topic},
        )
        self.owner.process_request_threaded(
            self.module.process_request,
            str(message.payload.decode("utf-8")),
            self.notifier_name,
        )
