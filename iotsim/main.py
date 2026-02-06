#!/usr/bin/env python
import argparse
import os
import time

import iotsim.core.iotcontainer as iot


def parse_arguments() -> str:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--config",
        help="Absolute path to <config>.json",
        action="store",
        default=os.path.normpath(
            os.path.dirname(os.path.abspath(__file__)) + "/../config"
        )
        + "/config-default.json",
    )
    args = parser.parse_args()
    if not args.config:
        raise iot.ProgramKilled
    else:
        return args.config


def main() -> None:
    json_config_file_path = parse_arguments()

    container = iot.IOTContainer(json_config_file_path)

    try:
        container.run()

        while True:
            time.sleep(0.5)

    except iot.ProgramKilled:
        container.shutdown()


if __name__ == "__main__":
    main()
