"""Thin async MQTT-backed appliance base class.

Subclasses implement domain-level getters/setters using the protected
`_get_path_*` accessors and `_send_command` helper. All transport,
state merging, presence tracking, and reconnect handling lives here.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, override

from ..appliance import Appliance as BaseAppliance
from ..types import ApplianceInfo
from .capabilities import CapabilityProfile
from .mqttclient import MqttClient

LOGGER = logging.getLogger(__name__)

INITIAL_STATE_TIMEOUT_SECONDS = 5.0
HEARTBEAT_INTERVAL_SECONDS = 60.0


def deep_merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge `update` into `base` in place. Returns `base`.

    When both sides have a dict at the same key, recurse. When types
    mismatch (e.g. dict vs scalar), keep the existing value and warn.
    """
    for key, new_value in update.items():
        existing = base.get(key)
        if isinstance(new_value, dict) and isinstance(existing, dict):
            deep_merge(existing, new_value)
        elif isinstance(existing, dict) and not isinstance(new_value, dict):
            LOGGER.warning(
                "deep_merge type mismatch at key %r (existing dict, update %s); "
                "keeping existing",
                key,
                type(new_value).__name__,
            )
        else:
            base[key] = new_value
    return base


class Appliance(BaseAppliance):
    """Base AWS IoT appliance."""

    def __init__(
        self,
        mqtt: MqttClient,
        appliance_info: ApplianceInfo,
        capability_profile: CapabilityProfile,
        initial_state_timeout: float = INITIAL_STATE_TIMEOUT_SECONDS,
        heartbeat_interval: float = HEARTBEAT_INTERVAL_SECONDS,
    ) -> None:
        super().__init__(appliance_info)
        self._mqtt = mqtt
        self._capability_profile = capability_profile
        self._initial_state_timeout = initial_state_timeout
        self._heartbeat_interval = heartbeat_interval

        self._state: dict[str, Any] = {}
        self._online: bool | None = None
        self._initial_state_event: asyncio.Event = asyncio.Event()
        self._heartbeat_task: asyncio.Task[None] | None = None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}> {self.said} | {self.name}"

    # --- public read-only ------------------------------------------------

    @property
    def capability_profile(self) -> CapabilityProfile:
        return self._capability_profile

    # --- topic builders --------------------------------------------------

    def _request_topic(self) -> str:
        return (
            f"cmd/{self.appliance_info.model_number}/{self.said}/request/"
            f"{self._mqtt.client_id}"
        )

    def _response_topic(self) -> str:
        return (
            f"cmd/{self.appliance_info.model_number}/{self.said}/response/"
            f"{self._mqtt.client_id}"
        )

    def _state_topic(self) -> str:
        return f"dt/{self.appliance_info.model_number}/{self.said}/state/update"

    def _presence_connected_topic(self) -> str:
        return f"$aws/events/presence/connected/{self.said}"

    def _presence_disconnected_topic(self) -> str:
        return f"$aws/events/presence/disconnected/{self.said}"

    # --- lifecycle -------------------------------------------------------

    async def connect(self) -> None:
        if self._mqtt.client_id is None:
            LOGGER.error(
                "Cannot connect appliance %s: MQTT client id not set", self.said
            )
            return

        await self._mqtt.subscribe(self._response_topic())
        await self._mqtt.subscribe(self._state_topic())
        await self._mqtt.subscribe(self._presence_connected_topic())
        await self._mqtt.subscribe(self._presence_disconnected_topic())

        self._mqtt.add_message_handler(self._handle_mqtt_message)
        self._mqtt.add_connection_handler(on_connect=self._on_reconnect)

        ok = await self.fetch_data()
        self._set_online(ok)

        if self._heartbeat_task is None and self._heartbeat_interval > 0:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def disconnect(self) -> None:
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None

        self._mqtt.remove_message_handler(self._handle_mqtt_message)
        for topic in (
            self._response_topic(),
            self._state_topic(),
            self._presence_connected_topic(),
            self._presence_disconnected_topic(),
        ):
            await self._mqtt.unsubscribe(topic)

    @override
    async def fetch_data(self) -> bool:
        self._initial_state_event.clear()
        await self._send_command_raw(addressee="appliance", command="getState")
        try:
            await asyncio.wait_for(
                self._initial_state_event.wait(),
                timeout=self._initial_state_timeout,
            )
            return True
        except TimeoutError:
            LOGGER.warning(
                "Timed out waiting for initial state of %s", self.said
            )
            return False

    @override
    def get_online(self) -> bool | None:
        return self._online

    @override
    def get_raw_data(self) -> dict[str, Any] | None:
        """Return the raw data dict for the appliance."""
        return self._state if self._state else None

    # --- protected helpers for subclasses --------------------------------

    def _get_path(self, path: str) -> Any | None:
        current: Any = self._state
        for part in path.split("."):
            if not isinstance(current, dict):
                return None
            current = current.get(part)
            if current is None:
                return None
        return current

    def _get_path_bool(self, path: str) -> bool | None:
        value = self._get_path(path)
        return value if isinstance(value, bool) else None

    def _get_path_int(self, path: str) -> int | None:
        value = self._get_path(path)
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        return None

    def _get_path_float(self, path: str) -> float | None:
        value = self._get_path(path)
        if isinstance(value, bool):
            return float(value)
        if isinstance(value, (int, float)):
            return float(value)
        return None

    def _get_path_str(self, path: str) -> str | None:
        value = self._get_path(path)
        return value if isinstance(value, str) else None

    async def _send_command(
        self, addressee: str, command: str, **payload_extra: Any
    ) -> None:
        await self._send_command_raw(addressee, command, **payload_extra)

    async def _send_command_raw(
        self, addressee: str, command: str, **payload_extra: Any
    ) -> None:
        if self._mqtt.client_id is None:
            LOGGER.error(
                "Cannot send command %s on %s: MQTT not connected",
                command,
                self.said,
            )
            return

        message: dict[str, Any] = {
            "requestId": str(uuid.uuid4()),
            "timestamp": int(time.time() * 1000),
            "payload": {
                "addressee": addressee,
                "command": command,
                **payload_extra,
            },
        }
        await self._mqtt.publish(self._request_topic(), message)

    # --- MQTT dispatch ---------------------------------------------------

    async def _handle_mqtt_message(
        self, topic: str, payload: dict[str, Any]
    ) -> None:
        if topic == self._response_topic():
            body = payload.get("payload") if isinstance(payload, dict) else None
            if isinstance(body, dict):
                deep_merge(self._state, body)
                self._initial_state_event.set()
                self._fire_attr_callbacks()
            return

        if topic == self._state_topic():
            if isinstance(payload, dict):
                deep_merge(self._state, payload)
                self._fire_attr_callbacks()
            return

        if topic == self._presence_connected_topic():
            self._set_online(True)
            asyncio.create_task(self._refetch_on_presence())
            return

        if topic == self._presence_disconnected_topic():
            self._set_online(False)
            return

    async def _refetch_on_presence(self) -> None:
        """Re-fetch state when the device comes back online."""
        try:
            await self.fetch_data()
        except Exception:
            LOGGER.exception(
                "Failed to refetch state after device presence for %s", self.said
            )

    async def _on_reconnect(self) -> None:
        try:
            ok = await self.fetch_data()
        except Exception:
            LOGGER.exception(
                "Failed to refetch state after reconnect for %s", self.said
            )
            return
        self._set_online(ok)

    async def _heartbeat_loop(self) -> None:
        """Periodically probe the device to recover from stale `_online` state.

        Presence events can be missed (e.g. we receive `disconnected` but the
        corresponding `connected` arrives while our own MQTT client is
        reconnecting), leaving `_online = False` indefinitely even though the
        device is reachable. A successful `getState` round-trip proves the
        device is online and fixes that.
        """
        while True:
            try:
                await asyncio.sleep(self._heartbeat_interval)
                if self._mqtt.client_id is None:
                    continue
                ok = await self.fetch_data()
                self._set_online(ok)
            except asyncio.CancelledError:
                raise
            except Exception:
                LOGGER.exception(
                    "Heartbeat iteration failed for %s", self.said
                )

    def _set_online(self, value: bool) -> None:
        if self._online == value:
            return
        self._online = value
        self._fire_attr_callbacks()

    def _fire_attr_callbacks(self) -> None:
        for cb in list(self._attr_changed):
            try:
                cb()
            except Exception:
                LOGGER.exception(
                    "attr_changed callback raised for %s", self.said
                )
