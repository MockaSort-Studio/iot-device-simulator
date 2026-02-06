import logging
import typedefines as types
import importlib


class DataSubscriber:
    def __init__(self, subscriber_cfg, owner):
        self.owner = owner
        self.id = subscriber_cfg["id"]
        self.type = subscriber_cfg["type"]
        self.topic = subscriber_cfg["topic"]
        self.register_subscriber(subscriber_cfg)

    def register_subscriber(self, cfg):
        try:
            self.owner.client.get_client.subscribe(self.topic)
            if self.type == types.DATA_WRITE_TYPE:
                self.register_write_key = cfg["write"]
                self.owner.client.get_client.message_callback_add(
                    self.topic, self.on_message_data_write
                )
            elif self.type == types.REQUEST_TYPE:
                self.module = importlib.import_module(cfg["request_module"])
                self.notifier_name = cfg["notifier"]
                self.owner.client.get_client.message_callback_add(
                    self.topic, self.on_message_request
                )
        except Exception:
            logging.error("register_subscriber -> %s failed", self.id)
            raise ValueError
        logging.info(
            "subscribed topic %(topic)s as %(type)s",
            {"topic": self.topic, "type": self.type},
        )

    def on_message_data_write(self, client, userdata, message):
        logging.debug(
            "received %(payload)s on topic %(topic)s",
            {"payload": message.payload, "topic": message.topic},
        )
        self.owner.set_register_value(
            self.register_write_key, str(message.payload.decode("utf-8"))
        )

    def on_message_request(self, client, userdata, message):
        logging.debug(
            "request %(payload)s received on topic %(topic)s",
            {"payload": message.payload, "topic": message.topic},
        )
        self.owner.process_request_threaded(
            self.module.process_request,
            str(message.payload.decode("utf-8")),
            self.notifier_name,
        )
