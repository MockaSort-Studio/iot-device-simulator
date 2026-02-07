#!/usr/bin/env python
import threading
from typing import Any, Dict


class StateRegistry:
    """A thread-safe 'shared dictionary' with minimal lock contention."""

    def __init__(self, initial_state: Dict[str, Any]) -> None:
        self._data = initial_state
        self._lock = threading.Lock()

    def update(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value

    def get_value(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)
