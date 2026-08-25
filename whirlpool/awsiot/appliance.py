import asyncio
import functools
import logging
import time
import uuid
from typing import Any, override

from ..appliance import Appliance as BaseAppliance
from ..awsiot.mqttclient import MqttClient
from ..types import ApplianceInfo

LOGGER = logging.getLogger(__name__)


def gated_set(support_check, label):
    """Gate a setter behind a capability check."""

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            if not support_check(self):
                LOGGER.warning("Model %s has no %s", self.said, label)
                return False
            return await func(self, *args, **kwargs)

        return wrapper

    return decorator


class Appliance(BaseAppliance):
    """Whirlpool awsiot appliance class"""

    def __init__(
        self,
        mqttclient: MqttClient,
        appliance_info: ApplianceInfo,
    ):
        super().__init__(appliance_info)
        self._mqttclient = mqttclient

        self._data_dict: dict[str, Any] = {}
        self._initial_data_event = asyncio.Event()
        self._online: bool | None = None

    def __repr__(self):
        return f"<{self.__class__.__name__}> {self.said} | {self.name}"

    async def subscribe_topics(self):
        """Subscribe to appliance topics."""
        if not self._mqttclient.client_id:
            LOGGER.error("MQTT client ID not set")
            return

        self._mqttclient.subscribe(
            f"cmd/{self.appliance_info.model_number}/{self.appliance_info.said}/response/{self._mqttclient.client_id}",
        )
        self._mqttclient.subscribe(
            f"dt/{self.appliance_info.model_number}/{self.appliance_info.said}/state/update",
        )
        self._mqttclient.subscribe(
            f"$aws/events/presence/connected/{self.appliance_info.said}",
        )
        self._mqttclient.subscribe(
            f"$aws/events/presence/disconnected/{self.appliance_info.said}",
        )

    def update_state(self, new_state: dict[str, Any]):
        """Merge a (possibly partial) state update and call callbacks.

        `dt/.../state/update` messages only carry the attributes that changed,
        so replacing the dict would drop everything else until the next
        getState round-trip.
        """
        self._data_dict = {**self._data_dict, **new_state}
        self._initial_data_event.set()
        for callback in self._attr_changed:
            callback()

    def update_online(self, online: bool):
        """Update presence state and call callbacks."""
        if self._online == online:
            return
        self._online = online
        for callback in self._attr_changed:
            callback()

    @override
    async def fetch_data(self) -> bool:
        """Fetch appliance data."""
        self._send_command("getState")
        try:
            await asyncio.wait_for(self._initial_data_event.wait(), timeout=30)
        except TimeoutError:
            LOGGER.error("Timeout waiting for data for appliance %s", self.said)
            return False
        return True

    @override
    def get_online(self) -> bool | None:
        """Get online state for appliance.

        Returns None until the first AWS IoT presence event is received.
        """
        return self._online

    @override
    def get_raw_data(self) -> dict[str, Any] | None:
        """Return the raw data dict for the appliance."""
        return self._data_dict if self._data_dict else None

    def _get_path(self, *path: str) -> Any | None:
        """Walk the state dict along `path`; return None if any step is missing."""
        value: Any = self._data_dict
        for key in path:
            if not isinstance(value, dict):
                return None
            value = value.get(key)
            if value is None:
                return None
        return value

    def _get_path_str(self, *path: str) -> str | None:
        value = self._get_path(*path)
        return value if isinstance(value, str) else None

    def _get_path_bool(self, *path: str) -> bool | None:
        value = self._get_path(*path)
        return value if isinstance(value, bool) else None

    def _get_path_int(self, *path: str) -> int | None:
        value = self._get_path(*path)
        if isinstance(value, bool):
            return None
        return int(value) if isinstance(value, (int, float)) else None

    def _get_path_float(self, *path: str) -> float | None:
        value = self._get_path(*path)
        if isinstance(value, bool):
            return None
        return float(value) if isinstance(value, (int, float)) else None

    def _send_command(self, command: str, payload_extra: dict | None = None):
        """Send a command to the appliance."""
        request_id = str(uuid.uuid4())
        timestamp = int(time.time() * 1000)  # Epoch milliseconds

        message = {
            "requestId": request_id,
            "timestamp": timestamp,
            "payload": {
                "addressee": "appliance",
                "command": command,
            },
        }
        if payload_extra:
            message["payload"].update(payload_extra)

        if not self._mqttclient.client_id:
            LOGGER.error("MQTT client ID not set")
            return

        self._mqttclient.publish(
            f"cmd/{self.appliance_info.model_number}/{self.appliance_info.said}/request/{self._mqttclient.client_id}",
            message,
        )
