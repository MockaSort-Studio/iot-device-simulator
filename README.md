# IoT Device Simulator


Python IoT device simulator consisting of an IoT Container running units representing IoT devices defined in a json file (see [iotunits.json](examples/iotunits.json)), a smart elevator and a temperature sensor implementation can be found in the [examples](examples) folder.

## Usage guide - Run examples

If you don't know what's uv -> [astral-uv](https://docs.astral.sh/uv)

Open folder in devcontainer, then you should be good to go

```
uv sync (optional)
```

create json config, use [config-default.json](iotsim/config/config-default.json) as template
```
{
    "logger": {
        "file_path": "/workspaces/iot-device-simulator/iotsim.log",
        "verbosity": "DEBUG"
    },
    "client": {
        "name": "test_client",
        "type": "mqtt",
        "host": "localhost",
        "port": 1883,
        "root_ca_path": "",
        "client_certificate_path": "",
        "client_key_path": ""
    },
    "units": {
        "units_list_file_path": "/workspaces/iot-device-simulator/examples/iotunits.json",
        "units_py_module_path": "/workspaces/iot-device-simulator/examples/"
    }
}

```


Run simulator
```
uv run iotsim/main.py --config <path-to-config.json>
```
if no argument are set the app will make use of the default config-default.json

Run simulator as Docker container
```
docker build -t <image-name> <path-do-dockerfile-parent-folder>
docker run --rm -d --network host --name <container-id> <image-name>
```
Read app log in docker container
```
docker exec -it <container-name> tail -f /workspace/iot-container.log
```

## Implement your own IoT Units

An IoT unit can be anything you wish, the package makes use of [importlib](https://docs.python.org/3/library/importlib.html) to import user defined module at runtime just by declaring them in the iotunits.json.

The Units make use of user defined registers (simulating the volatile memory of the device) to manipulate and share data between control_loop, publishers and subscribers. Register works in a dictionary fashion and the keys and init value must be defined in the json definition of your unit.

```
{
    "name": "iot-unit", #name of the unit
    "control_loop_module": "user-define-unit.control-loop-module", #null if periodic activity is not needed
    "control_loop_sleep_ms": cyle_time, #cycle time of the periodic activity
    "registers": {}, #register
    "publishers": [{...}], #publishers list
    "subscribers": [{...}] #subscribers list
}
```
##### Control loop
Unit package structure

```
|-- user-defined-unit/
    |-- __init__.py
    |-- control-loop-module.py

```
Control loop function must have the signature below:
```
        iotsim.core.stateregistry.StateRegistry
            |
def run(registers,):
    #TODO Implement your logic
    #registers.update('key', some-value)
    #registers.get_value('key')
```
##### Publishers

Publishers are mapped to a register key and publish, with a given frequency, the value corresponding to the key.

Json definition
```
{
    "id": "publisher-id",
    "publish_frequency_ms",       #publish frequency in ms
    "read": "register-key",       #register key accessed by publisher
    "topic": "mqtt-topic"         #mqtt-topic of the subscription
}
```
##### Subscribers

Subscribers are triggered by a message received on their mqtt-topic and write some data received on topic to the register value they're mapped to

Json definition
```
{
    "id": "subscriber-id",
    "write": "register-key",         #register key accessed by subscriber
    "topic": "unit/robot_request"    #mqtt-topic of the subscription
}
```

## TODO LIST

- [x] Code clean up
- [x] Unit testing
- [ ] Improve documentation
- [x] Improve overall abstraction
- [x] Improve Python packaging
- [ ] Refactor project in order to make use of an arbitrary communication protocol

## Contributors

* [Michelangelo Setaro](https://github.com/mksetaro)

## Contribution

If you wish to contribute get in touch with **MockaSort-Studio**
  * mockasortstudio@gmail.com
  * [MockaSort Studio - Discord](https://discord.gg/z2DAWmcy)
