import random
import logging


def run(
    registers,
):
    if registers["status"] == "ON":
        registers["temperature"] = random.uniform(1.5, 1.9)
        logging.info("current temperature %f", registers["temperature"])
    elif registers["status"] == "OFF":
        logging.warning("temperature sensor turned off %s", registers["status"])
    else:
        logging.error("corrupted register -> %s restarting sensor", "status")
        registers["status"] = "ON"
