import logging
import time
import uuid
from collections.abc import Callable
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
        # self._mqtt.subscribe(
        #     f"api/capability/download/{self.appliance_info.model_number}/{self.appliance_info.said}/response",
        # )
        # self._mqtt.publish(
        #     f"api/capability/download/{self.appliance_info.model_number}/{self.appliance_info.said}",
        #     {"capabilityPartNumber": f"{thing_attrs.get('CapabilityPartNumber', '')}"},
        # )

    def update_state(self, new_state: dict[str, Any]):
        """Update appliance state and call callbacks."""
        self._data_dict = new_state
        for callback in self._attr_changed:
            callback()

    @override
    async def fetch_data(self) -> bool:
        """Fetch appliance data from web api"""
        self._send_command("getState")
        # TODO: wait for response?
        return True

    @override
    def get_online(self) -> bool | None:
        """Get online state for appliance"""
        raise NotImplementedError

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
