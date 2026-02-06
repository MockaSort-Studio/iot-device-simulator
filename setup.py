from setuptools import setup, find_packages

setup(
    name="iot-device-simulator",
    version="1.1.0",
    packages=find_packages(include=["iotsim", "iotsim.*"]),
    install_requires=[
        "paho-mqtt==1.6.1",
        "schedule==1.1.0",
        "json-schema-codegen==0.6.1",
    ],
)
