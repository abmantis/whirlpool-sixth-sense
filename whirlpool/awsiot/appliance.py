import asyncio
import logging
import time
import uuid
from typing import Any, override

from ..appliance import Appliance as BaseAppliance
from ..awsiot.mqttclient import MqttClient
from ..types import ApplianceInfo

LOGGER = logging.getLogger(__name__)


class Appliance(BaseAppliance):
    """Whirlpool awsiot appliance class"""

    def __init__(
        self,
        mqttclient: MqttClient,
        appliance_info: ApplianceInfo,
    ):
        super().__init__(appliance_info)
        self._mqttclient = mqttclient

        self._data_dict: dict = {}
        self._initial_data_event = asyncio.Event()

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

        # TODO: implement capability download and handling
        # model = self.appliance_info.model_number
        # said = self.appliance_info.said
        # thing_attrs is not available in subscribe_topics(); obtain it before
        # this call (for example, pass it into this method or store it on self).
        # self._mqttclient.subscribe(
        #     f"api/capability/download/{model}/{said}/response"
        # )
        # self._mqttclient.publish(
        #     f"api/capability/download/{model}/{said}",
        #     {"capabilityPartNumber": thing_attrs.get("CapabilityPartNumber", "")},
        # )

    def update_state(self, new_state: dict[str, Any]):
        """Update appliance state and call callbacks."""
        self._data_dict = new_state
        self._initial_data_event.set()
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
        """Get online state for appliance"""
        raise NotImplementedError

    @override
    def get_raw_data(self) -> dict[str, Any] | None:
        """Return the raw data dict for the appliance."""
        return self._data_dict if self._data_dict else None

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
