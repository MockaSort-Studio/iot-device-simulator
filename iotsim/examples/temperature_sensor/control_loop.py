import logging
import random


def run(
    registers: "iotsim.core.stateregistry.StateRegistry",
) -> None:
    if registers.get_value("status") == "ON":
        registers.update("temperature", random.uniform(1.5, 1.9))
        logging.info("current temperature %f", registers.get_value("temperature"))
    elif registers.get_value("status") == "OFF":
        logging.warning(
            "temperature sensor turned off %s", registers.get_value("status")
        )
    else:
        logging.error("corrupted register -> %s restarting sensor", "status")
        registers.update("status", "ON")
