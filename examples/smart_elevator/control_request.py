import json
import time


def process_request(registers, payload, notify_func):
    json_payload = json.loads(payload)
    response = registers["elevator_info"]
    if json_payload["cmd"] == "call":
        response["door"] = "close"
        response["floor"] = json_payload["floor"] + 5
        response["recv_cmd"] = "call"
        registers["elevator_res"] = json.dumps(response)
        time.sleep(1)
        notify_func()  # notify reception of command
        response["door"] = "open"
        response["floor"] = json_payload["floor"]
        time.sleep(5)
        registers["elevator_res"] = json.dumps(response)
        notify_func()  # notify elevator at destination
    elif json_payload["cmd"] == "open":
        response["recv_cmd"] = "open"
        registers["elevator_res"] = json.dumps(response)
        time.sleep(1)
        notify_func()
    elif json_payload["cmd"] == "destination":
        response["recv_cmd"] = "destination"
        registers["requested_floor"] = json_payload["floor"]
        registers["elevator_res"] = json.dumps(response)
        time.sleep(1)
        notify_func()
    elif json_payload["cmd"] == "close":
        response["door"] = "close"
        response["recv_cmd"] = "close"
        registers["elevator_res"] = json.dumps(response)
        time.sleep(1)
        notify_func()
        if response["floor"] != registers["requested_floor"]:
            time.sleep(5)
            response["floor"] = registers["requested_floor"]
            response["door"] = "open"
            registers["elevator_res"] = json.dumps(response)
            notify_func()
