import signal
import threading
from typing import Any, Callable
from unittest.mock import MagicMock, mock_open, patch

import orjson as json
import pytest

import iotsim.config.types as tp
from iotsim.core.datapublisher import DataPublisher
from iotsim.core.datasubscriber import DataSubscriber
from iotsim.core.iotcontainer import IOTContainer, ProgramKilled
from iotsim.core.iotunit import IOTUnit
from iotsim.core.networkclients import MQTTNetworkInterface, NetworkInterfaceBuilder
from iotsim.core.stateregistry import StateRegistry


def test_data_publisher() -> None:
    """Test DataPublisher publish method with mocked registry and client."""
    mock_model = MagicMock()
    mock_model.read = "sensor_1"
    mock_model.topic = "telemetry/v1"
    mock_model.publish_frequency_ms = 1000

    mock_client = MagicMock()
    mock_registry = MagicMock()

    mock_registry.get_value.return_value = {"temperature": 22.5}

    publisher = DataPublisher(
        publisher_model=mock_model, client=mock_client, data_registry=mock_registry
    )

    try:
        publisher.publish()
    except Exception as e:
        pytest.fail(f"Smoke test failed: publish() raised an exception: {e}")

    mock_registry.get_value.assert_called_once_with("sensor_1")
    expected_payload = b'{"temperature":22.5}'
    mock_client.publish.assert_called_once_with("telemetry/v1", expected_payload)


def test_data_subscriber() -> None:
    """Test DataSubscriber subscription and message handling."""
    mock_model = MagicMock()
    mock_model.topic = "commands/engine_speed"
    mock_model.write = "reg_engine_01"

    mock_client = MagicMock()
    mock_registry = MagicMock()

    subscriber = DataSubscriber(
        subscriber_model=mock_model,
        network_client=mock_client,
        data_registry=mock_registry,
    )

    mock_client.subscribe.assert_called_once_with(
        "commands/engine_speed", subscriber.on_message_data_write
    )

    test_payload = "4500"
    subscriber.on_message_data_write(test_payload)

    mock_registry.update.assert_called_once_with("reg_engine_01", "4500")


def test_state_registry_basic_operations() -> None:
    """Test StateRegistry get and update operations."""
    initial = {"temp": 20, "rpm": 1000}
    registry = StateRegistry(initial)

    # Test update
    registry.update("temp", 25)
    assert registry.get_value("temp") == 25

    # Test default value for non-existent key
    assert registry.get_value("pressure", default=101.3) == 101.3


def test_state_registry_thread_safety() -> None:
    """Test StateRegistry thread safety under concurrent increments."""
    registry = StateRegistry({"counter": 0})
    num_threads = 10
    increments_per_thread = 1000

    def worker() -> None:
        """Increment counter multiple times to test thread safety."""
        for _ in range(increments_per_thread):
            # We must get, then update to simulate a read-modify-write race condition
            current = registry.get_value("counter")
            registry.update("counter", current + 1)

    threads: list[threading.Thread] = [
        threading.Thread(target=worker) for _ in range(num_threads)
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # If thread safety is working, the result must be exactly (threads * increments)
    assert registry.get_value("counter") == (num_threads * increments_per_thread)


@pytest.fixture
def mock_mqtt_config() -> MagicMock:
    """Create a mock MQTT config with SSL certificate paths."""
    config = MagicMock()
    config.name = "test_device"
    config.type = "mqtt"
    config.host = "localhost"
    config.port = 8883
    config.root_ca_path = "/fake/ca.crt"
    config.client_certificate_path = "/fake/client.crt"
    config.client_key_path = "/fake/client.key"
    return config


def test_builder_creates_correct_instance(mock_mqtt_config: MagicMock) -> None:
    """Test NetworkInterfaceBuilder creates MQTTNetworkInterface instance."""
    with patch("paho.mqtt.client.Client"), patch("ssl.create_default_context"):
        interface = NetworkInterfaceBuilder.build(mock_mqtt_config)
        assert isinstance(interface, MQTTNetworkInterface)


def test_mqtt_initialization_flow(mock_mqtt_config: MagicMock) -> None:
    """Test MQTT interface initializes SSL context and connects."""
    with (
        patch("paho.mqtt.client.Client") as MockPaho,
        patch("ssl.create_default_context") as MockSSL,
    ):
        mock_paho_instance = MockPaho.return_value

        NetworkInterfaceBuilder.build(mock_mqtt_config)

        MockSSL.assert_called_once()
        mock_paho_instance.tls_set_context.assert_called_once()
        mock_paho_instance.connect.assert_called_once_with("localhost", 8883)


def test_subscribe_callback_adaptation(mock_mqtt_config: MagicMock) -> None:
    """Test MQTT bytes payload is decoded to string before user callback."""
    with patch("paho.mqtt.client.Client"), patch("ssl.create_default_context"):
        interface = NetworkInterfaceBuilder.build(mock_mqtt_config)

        # Setup a dummy callback and simulate a Paho message object
        user_callback: MagicMock = MagicMock()
        mock_message = MagicMock()
        mock_message.topic = "test/topic"
        mock_message.payload = b"45.5"  # MQTT sends bytes

        # Hook it up
        interface.subscribe("test/topic", user_callback)

        # Extract the internal function 'on_message' added via message_callback_add
        # call_args[0][1] is the internal wrapper function
        internal_wrapper: Callable[[Any, Any, Any], None] = (
            interface._client.message_callback_add.call_args[0][1]
        )

        # Trigger the internal wrapper
        internal_wrapper(None, None, mock_message)

        # Verify the user callback received a STRING, not BYTES
        user_callback.assert_called_once_with("45.5")


@pytest.fixture
def mock_unit_model() -> tp.UnitModel:
    """Create a UnitModel with publisher, subscriber, and control loop."""
    pub_json = {
        "id": "pub1",
        "topic": "tele/rpm",
        "read": "rpm",
        "publish_frequency_ms": 100,
    }
    sub_json = {"id": "sub1", "topic": "cmd/rpm", "write": "rpm"}
    return tp.UnitModel(
        name="engine_01",
        registers={"rpm": 0, "temp": 20},
        publishers=[tp.PublisherModel(**pub_json)],
        subscribers=[tp.SubscriberModel(**sub_json)],
        control_loop_module="unittest.mock",  # We use a real existing module to pass importlib
        control_loop_sleep_ms=500,
    )


def test_iot_unit_initialization(mock_unit_model: tp.UnitModel) -> None:
    """Test IOTUnit initializes state, publishers, subscribers, and scheduler."""
    mock_client = MagicMock()
    mock_scheduler = MagicMock()

    with patch("unittest.mock.run", create=True) as mock_loop_run:
        unit = IOTUnit(
            unit_model=mock_unit_model, client=mock_client, scheduler=mock_scheduler
        )

        assert unit.state_registry.get_value("temp") == 20
        assert unit.name == "engine_01"

        mock_scheduler.add_job.assert_any_call(
            unit.publishers["pub1"].publish,
            "interval",
            seconds=0.1,
            coalesce=False,
            max_instances=1,
        )

        mock_client.subscribe.assert_called_once_with(
            "cmd/rpm", unit.subscribers["sub1"].on_message_data_write
        )

        mock_scheduler.add_job.assert_any_call(
            mock_loop_run,
            "interval",
            seconds=0.5,
            args=[unit.state_registry],
            coalesce=False,
            max_instances=1,
        )


def test_iot_unit_invalid_module_raises_error(mock_unit_model: tp.UnitModel) -> None:
    """Test IOTUnit raises ValueError for invalid control loop module path."""
    mock_unit_model.control_loop_module = "non.existent.module.path"

    with pytest.raises(ValueError):
        IOTUnit(mock_unit_model, MagicMock(), MagicMock())


@pytest.fixture
def mock_configs():
    """Return real Pydantic model instances for logger, client, and units config."""
    logger = tp.LoggerConfig(file_path="test.log", verbosity="INFO")
    client = tp.ClientConfig(
        name="boss_client",
        host="localhost",
        port=1883,
        root_ca_path="ca.crt",
        client_certificate_path="c.crt",
        client_key_path="c.key",
    )
    units = tp.UnitsConfig(
        units_list_file_path="units_list.json", units_py_module_path="."
    )
    return logger, client, units


def test_container_signal_handling(mock_configs) -> None:
    """Verify that the signal handler correctly triggers shutdown logic."""
    l_cfg, c_cfg, u_cfg = mock_configs

    # 1. Mock the control loop module so it doesn't crash on import
    mock_loop = MagicMock()
    mock_loop.run = lambda x: x

    # 2. Sequential File Mocking
    # First call (load_config) gets a dict, second call (init_units) gets a list
    config_json = b'{"logger":{}, "client":{}, "units":{}}'
    units_json = b"[]"

    m_open = mock_open()
    m_open.side_effect = [
        mock_open(read_data=config_json).return_value,
        mock_open(read_data=units_json).return_value,
    ]

    # 3. Execution with all patches
    with (
        patch("iotsim.config.types.parse_config", return_value=(l_cfg, c_cfg, u_cfg)),
        patch(
            "iotsim.core.networkclients.NetworkInterfaceBuilder.build",
            return_value=MagicMock(),
        ),
        patch("iotsim.core.iotcontainer.IOTContainer.init_units"),
        patch("builtins.open", m_open),
        patch.dict("sys.modules", {"unittest.mock": mock_loop}),
    ):
        # Initialize
        container = IOTContainer("dummy.json")

        with pytest.raises(ProgramKilled):
            container.signal_handler(signal.SIGINT, None)

        assert container.shutdown_flag.is_set()


def test_container_full_run_and_shutdown(mock_configs) -> None:
    """Verify the start/stop orchestration of the entire container."""
    l_cfg, c_cfg, u_cfg = mock_configs
    mock_loop = MagicMock()
    mock_loop.run = lambda x: x

    # Use valid empty JSONs for both file reads
    m_open = mock_open()
    m_open.side_effect = [
        mock_open(read_data=b"{}").return_value,
        mock_open(read_data=b"[]").return_value,
    ]

    with (
        patch("iotsim.config.types.parse_config", return_value=(l_cfg, c_cfg, u_cfg)),
        patch("iotsim.core.networkclients.NetworkInterfaceBuilder.build") as m_build,
        patch("iotsim.core.iotcontainer.IOTContainer.init_units"),
        patch("builtins.open", m_open),
        patch.dict("sys.modules", {"unittest.mock": mock_loop}),
    ):
        mock_client = MagicMock()
        m_build.return_value = mock_client

        container = IOTContainer("dummy.json")

        # Test Run
        container.run()
        mock_client.start.assert_called_once()
        assert container.scheduler.running is True

        # Test Shutdown
        container.shutdown()
        mock_client.stop.assert_called_once()
        assert container.scheduler.running is False


def test_container_load_config_error() -> None:
    """Test IOTContainer raises ProgramKilled on malformed config file."""
    with patch("builtins.open", mock_open(read_data=b"invalid json")):
        with pytest.raises(ProgramKilled):
            IOTContainer("bad_config.json")


def test_container_loads_from_custom_path(mock_configs):
    """Test the container loads a file from a provided string path."""
    l_cfg, c_cfg, u_cfg = mock_configs

    # Mock data: One for config, one for units list
    config_json = b'{"logger":{}, "client":{}, "units":{}}'
    units_json = b"[]"

    m_open = mock_open()
    m_open.side_effect = [
        mock_open(read_data=config_json).return_value,
        mock_open(read_data=units_json).return_value,
    ]

    with (
        patch("builtins.open", m_open),
        patch("iotsim.config.types.parse_config", return_value=(l_cfg, c_cfg, u_cfg)),
        patch(
            "iotsim.core.networkclients.NetworkInterfaceBuilder.build",
            return_value=MagicMock(),
        ),
        patch("iotsim.core.iotcontainer.IOTContainer.init_units"),
        patch.dict("sys.modules", {"unittest.mock": MagicMock()}),
    ):
        _ = IOTContainer("custom_config.json")

        # Verify open was called with the custom path
        m_open.assert_any_call("custom_config.json", "rb")


def test_container_loads_from_resources_on_empty_path(mock_configs):
    """Test default config triggers importlib.resources for config and units."""
    l_cfg, c_cfg, u_cfg = mock_configs
    # Ensure paths are blank to trigger fallback
    u_cfg.units_list_file_path = ""
    u_cfg.units_py_module_path = ""

    # 1. Prepare Mock Data
    mock_config_json = b'{"logger":{}, "client":{}, "units":{}}'
    mock_units_json = b"[]"  # orjson handles this byte-string perfectly

    with (
        patch("importlib.resources.files") as m_res_files,
        # We no longer need mock_open because init_units now uses resources.files too!
        patch("iotsim.config.types.parse_config", return_value=(l_cfg, c_cfg, u_cfg)),
        patch(
            "iotsim.core.networkclients.NetworkInterfaceBuilder.build",
            return_value=MagicMock(),
        ),
        patch.dict("sys.modules", {"unittest.mock": MagicMock()}),
    ):
        # 2. Setup the side_effect for sequential calls to read_bytes()
        # Call 1: load_config -> config/default.json
        # Call 2: init_units -> examples/iotunits.json
        m_res_files.return_value.joinpath.return_value.read_bytes.side_effect = [
            mock_config_json,
            mock_units_json,
        ]

        # ACT: Pass empty string to trigger fallback
        container = IOTContainer("")

        # 3. ASSERT: verify resources were used for both config and examples
        # Check packages accessed
        m_res_files.assert_any_call("iotsim.config")
        m_res_files.assert_any_call("iotsim.examples")

        # Check specific files targeted
        # Note: We use .call_args_list if we want to be strict about the filenames
        filenames = [
            call.args[0] for call in m_res_files.return_value.joinpath.call_args_list
        ]
        assert "config-default.json" in filenames
        assert "iotunits.json" in filenames

        # Verify units were initialized (empty list in this case)
        assert container.unit_register == {}


def test_container_failed_load_raises_program_killed():
    """Test both paths fail and ProgramKilled is raised."""
    with (
        patch("builtins.open", side_effect=FileNotFoundError("Missing file")),
        patch("importlib.resources.files", side_effect=Exception("Resource error")),
    ):
        with pytest.raises(ProgramKilled):
            IOTContainer("non_existent.json")


def test_container_init_units_registration(mock_configs):
    """Verify unit loop triggers and populates unit_register with mocked imports."""
    l_cfg, c_cfg, u_cfg = mock_configs
    u_cfg.units_list_file_path = ""

    # 1. Prepare data for 1 unit pointing to a dummy module
    unit_data = {"name": "thermometer_01", "control_loop_module": "mock_loop_mod"}
    mock_units_json = json.dumps([unit_data])
    mock_config_json = json.dumps({"logger": {}, "client": {}, "units": {}})

    # We need to mock the module so importlib doesn't explode
    mock_module = MagicMock()
    mock_module.run = lambda x: x

    with (
        patch("importlib.resources.files") as m_res,
        patch("iotsim.config.types.parse_config", return_value=(l_cfg, c_cfg, u_cfg)),
        patch("iotsim.config.types.parse_unit_from_json") as m_parse_unit,
        patch("iotsim.core.iotunit.IOTUnit") as m_unit_class,
        patch("iotsim.core.networkclients.NetworkInterfaceBuilder.build"),
        # Mock the actual import process
        patch("importlib.import_module", return_value=mock_module),
        patch.dict("sys.modules", {"mock_loop_mod": mock_module}),
    ):
        # Setup resource fallback sequence
        m_res.return_value.joinpath.return_value.read_bytes.side_effect = [
            mock_config_json,
            mock_units_json,
        ]

        # Setup unit parsing mock
        mock_unit_model = MagicMock()
        mock_unit_model.name = "thermometer_01"
        mock_unit_model.control_loop_module = "mock_loop_mod"
        mock_unit_model.control_loop_sleep_ms = 500
        m_parse_unit.return_value = mock_unit_model

        # ACT: Initialize the container
        container = IOTContainer("")

        # ASSERT: verify registration logic
        m_parse_unit.assert_called_once_with(unit_data)
        # m_unit_class.assert_called_once()
        assert "thermometer_01" in container.unit_register

        # Verify that the mocked unit was stored in our register
        assert type(container.unit_register["thermometer_01"]) is IOTUnit


def test_container_init_units_failure_raises_error(mock_configs):
    """Test init_units exception block is triggered and raises ValueError."""
    l_cfg, c_cfg, u_cfg = mock_configs

    # Force an error by providing invalid JSON structure for the loop
    mock_units_json = b"invalid-json-structure"

    with (
        patch("importlib.resources.files") as m_res,
        patch("iotsim.config.types.parse_config", return_value=(l_cfg, c_cfg, u_cfg)),
        patch("iotsim.core.networkclients.NetworkInterfaceBuilder.build"),
    ):
        m_res.return_value.joinpath.return_value.read_bytes.side_effect = [
            json.dumps({}),  # Config
            mock_units_json,  # This will cause orjson.loads to raise an error
        ]

        # ASSERT: The Exception block is triggered and raises ValueError
        with pytest.raises(ValueError):
            IOTContainer("")
