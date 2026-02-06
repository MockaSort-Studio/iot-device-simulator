#!/usr/bin/env python
import logging
import ssl
from abc import ABC, ABCMeta, abstractmethod
from enum import Enum
from threading import Lock
from typing import Optional

import paho.mqtt.client as mqtt

from iotsim.config.types import ClientConfig


class SingletonMeta(ABCMeta):
    _instances = {}
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]


class Client(ABC, metaclass=SingletonMeta):
    _lock: Lock = Lock()

    def __init__(self, client_cfg: ClientConfig) -> None:
        self._client: Optional[mqtt.Client] = None
        self._init_client(client_cfg)

    @property
    def client(self):
        with self._lock:
            if self._client is None:
                raise RuntimeError("Client not initialized")
            return self._client

    def start(self) -> None:
        with self._lock:
            self._start()

    def stop(self) -> None:
        with self._lock:
            self._stop()

    @abstractmethod
    def _init_client(self, client_cfg: ClientConfig) -> None:
        pass

    @abstractmethod
    def _start(self) -> None:
        pass

    @abstractmethod
    def _stop(self) -> None:
        pass


class MQTTClient(Client):
    def __init__(self, client_cfg: ClientConfig) -> None:
        self.name: str = ""
        self.ssl_context: Optional[ssl.SSLContext] = None
        super().__init__(client_cfg)

    def _init_client(self, client_cfg: ClientConfig) -> None:
        self.name = client_cfg.id
        self._init_mqtt_client(client_cfg)

    def _init_mqtt_client(self, client_cfg: ClientConfig) -> None:
        try:
            self._client = mqtt.Client(client_id=self.name)

            if (
                client_cfg.root_ca_path
                and client_cfg.client_certificate_path
                and client_cfg.client_key_path
            ):
                self._init_ssl_context(client_cfg)
                self._client.tls_set_context(self.ssl_context)

            self._client.connect(client_cfg.host, client_cfg.port)
        except Exception as e:
            logging.error(
                "Failed to initialize MQTT connection for %s: %s", self.name, e
            )
            raise ValueError(
                f"MQTT client initialization failed for {self.name}"
            ) from e

        logging.info(
            "MQTT client '%s' connected to %s:%s",
            self.name,
            client_cfg.host,
            client_cfg.port,
        )

    def _init_ssl_context(self, client_cfg: ClientConfig) -> None:
        try:
            self.ssl_context = ssl.create_default_context()
            self.ssl_context.load_verify_locations(client_cfg.root_ca_path)
            self.ssl_context.load_cert_chain(
                client_cfg.client_certificate_path,
                client_cfg.client_key_path,
            )
        except Exception as e:
            logging.error("Failed to initialize SSL context for %s: %s", self.name, e)
            raise ValueError(
                f"SSL context initialization failed for {self.name}"
            ) from e

        logging.info("SSL context created for '%s'", self.name)

    def _start(self) -> None:
        if self._client and hasattr(self._client, "loop_start"):
            self._client.loop_start()

    def _stop(self) -> None:
        if (
            self._client
            and hasattr(self._client, "loop_stop")
            and hasattr(self._client, "disconnect")
        ):
            self._client.loop_stop()
            self._client.disconnect()


class ClientType(Enum):
    MQTT = "mqtt"
    NONE = "none"


class ClientBuilder:
    _TYPE_MAP = {ClientType.MQTT.value: MQTTClient}

    @staticmethod
    def build(client_cfg: ClientConfig) -> Client:
        client_type = client_cfg.type

        if client_type not in ClientBuilder._TYPE_MAP:
            raise ValueError(f"Unsupported client type: {client_type}")

        client_class = ClientBuilder._TYPE_MAP[client_type]
        return client_class(client_cfg)
