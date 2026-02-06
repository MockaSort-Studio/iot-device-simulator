#!/usr/bin/env python
import ssl
import schedule
import time
import threading
import logging
from os import sys, environ
import signal
from iotunit import IOTUnit
import json
import generated_parameters as params
from networkclients import ClientBuilder


class ProgramKilled(Exception):
    pass


class IOTContainer:
    def __init__(self, json_config_file_path):
        logger_cfg, client_cfg, pods_cfg = self.load_config(json_config_file_path)
        sys.path.append(pods_cfg.GetPodsPyModulePath().Get())
        logging.basicConfig(
            filename=logger_cfg.GetFilePath().Get(),
            filemode="w",
            format="%(asctime)s -%(levelname)s- %(message)s",
            level=logger_cfg.GetVerbosity().Get(),
        )
        self.bind_signal_handlers()
        self.setup_daemon_thread()
        self.setup_client(client_cfg)
        self.init_pods(pods_cfg)

    def load_config(self, json_config_file_path):
        try:
            json_config = json.load(open(json_config_file_path))
            parameters = params.Parameters(json_config)
            return parameters.GetLogger(), parameters.GetClient(), parameters.GetPods()
        except IOError:
            raise ProgramKilled
        except json.decoder.JSONDecodeError:
            raise ProgramKilled

    def bind_signal_handlers(self):
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, signum, frame):
        self.shutdown_flag.set()
        logging.info("shutdown signal received")
        raise ProgramKilled

    def setup_daemon_thread(self):
        self.shutdown_flag = threading.Event()
        self.scheduler = schedule
        self.scheduler_thread = threading.Thread(
            name="scheduler daemon", target=self.daemon_scheduler
        )
        self.scheduler_thread.setDaemon(True)

    def setup_client(self, client_cfg):
        self.client = ClientBuilder.build(client_cfg)

    def init_pods(self, pods_cfg):
        self.pods_map = {}
        try:
            pods_list = json.load(open(pods_cfg.GetPodsListFilePath().Get()))
            for pod in pods_list:
                pod_tmp = IOTUnit(pod, self.client, self.scheduler)
                self.pods_map[pod["name"]] = pod_tmp
        except Exception:
            logging.error("init iot units failed")
            raise ValueError
        logging.info("iot units initialized -> %s", self.pods_map.keys())

    def daemon_scheduler(self):
        while not self.shutdown_flag.is_set():
            self.scheduler.run_pending()
            time.sleep(0.5)
        logging.info("scheduler daemon clean shutdown")
        self.scheduler.clear()
        logging.info("scheduler stopped")

    def run(self):
        logging.info("starting container")
        self.scheduler_thread.start()
        self.client.start()

    def shutdown(self):
        logging.info("stopping container")
        self.scheduler_thread.join()
        self.client.stop()
