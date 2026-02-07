#!/usr/bin/env python
import logging
import ssl
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Optional

import paho.mqtt.client as mqtt
from config.types import ClientConfig


class NetworkInterface(ABC):
    def __init__(self, client_cfg: ClientConfig) -> None:
        self._init_client(client_cfg)
        logging.info(f"Initialized {self.__class__.__name__}")

    @abstractmethod
    def _init_client(self, client_cfg: ClientConfig) -> None: ...

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def publish(self, topic: str, payload: Any) -> None: ...

    @abstractmethod
    def subscribe(self, topic: str, on_message_callback: Callable) -> None: ...


class MQTTNetworkInterface(NetworkInterface):
    _ssl_context: Optional[ssl.SSLContext] = None
    _client: mqtt.Client

    def __init__(self, client_cfg: ClientConfig) -> None:
        super().__init__(client_cfg)

    def _init_client(self, client_cfg: ClientConfig) -> None:
        self._init_mqtt_client(client_cfg)

    def start(self) -> None:
        if self._client:
            self._client.loop_start()

    def stop(self) -> None:
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()

    def publish(self, topic: str, payload: Any) -> None:
        if self._client:
            self._client.publish(topic, payload)

    def subscribe(self, topic: str, on_message_callback: Callable) -> None:
        if self._client:
            self._client.message_callback_add(topic, on_message_callback)
            self._client.subscribe(topic)

    def _init_mqtt_client(self, client_cfg: ClientConfig) -> None:
        try:
            self._client = mqtt.Client(client_id=client_cfg.name)

            if (
                client_cfg.root_ca_path
                and client_cfg.client_certificate_path
                and client_cfg.client_key_path
            ):
                self._init_ssl_context(client_cfg)
                self._client.tls_set_context(self._ssl_context)

            self._client.connect(client_cfg.host, client_cfg.port)
        except Exception as e:
            logging.error(
                "Failed to initialize MQTT connection for %s: %s", client_cfg.name, e
            )
            raise ValueError(
                f"MQTT client initialization failed for {client_cfg.name}"
            ) from e

        logging.info(
            "MQTT client '%s' connected to %s:%s",
            client_cfg.name,
            client_cfg.host,
            client_cfg.port,
        )

    def _init_ssl_context(self, client_cfg: ClientConfig) -> None:
        try:
            self._ssl_context = ssl.create_default_context()
            self._ssl_context.load_verify_locations(client_cfg.root_ca_path)
            self._ssl_context.load_cert_chain(
                client_cfg.client_certificate_path,
                client_cfg.client_key_path,
            )
        except Exception as e:
            logging.error(
                "Failed to initialize SSL context for %s: %s", client_cfg.name, e
            )
            raise ValueError(
                f"SSL context initialization failed for {client_cfg.name}"
            ) from e

        logging.info("SSL context created for '%s'", client_cfg.name)


class ProtocolType(Enum):
    MQTT = "mqtt"
    NONE = "none"


class NetworkInterfaceBuilder:
    _TYPE_MAP = {ProtocolType.MQTT.value: MQTTNetworkInterface}

    @staticmethod
    def build(client_cfg: ClientConfig) -> NetworkInterface:
        client_type = client_cfg.type

        if client_type not in NetworkInterfaceBuilder._TYPE_MAP:
            raise ValueError(f"Unsupported client type: {client_type}")

        client_class = NetworkInterfaceBuilder._TYPE_MAP[client_type]
        return client_class(client_cfg)
