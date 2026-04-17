"""Whirlpool AWS IoT MQTT Client"""

import asyncio
import json
import logging
import secrets
import ssl
import urllib.parse
from collections.abc import Callable
from typing import Any

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion, MQTTProtocolVersion
from paho.mqtt.properties import Properties
from paho.mqtt.reasoncodes import ReasonCode

from .auth import Auth

LOGGER = logging.getLogger(__name__)

MQTT_ENDPOINT = "wt.applianceconnect.net"
RECONNECT_BACKOFF_INITIAL_SECONDS = 1.0
RECONNECT_BACKOFF_CAP_SECONDS = 30.0


def _generate_client_id(identity_id: str) -> str:
    """Generate a client ID in the format used by the Android app."""
    random_suffix = secrets.token_hex(8)  # 16 hex chars
    return f"{identity_id}_{random_suffix}"


class MqttClient:
    """Async MQTT client for Whirlpool appliance communication."""

    def __init__(
        self,
        aws_auth: Auth,
        message_callback: Callable[[str, dict[str, Any]], None] | None = None,
    ):
        """Initialize MQTT client."""
        self._aws_auth = aws_auth
        self._message_callback = message_callback
        self._client: mqtt.Client | None = None
        self._connected = asyncio.Event()
        self._subscribed_topics: set[str] = set()
        self._client_id: str | None = None

        self._loop = asyncio.get_running_loop()
        self._reconnect_task: asyncio.Task[None] | None = None
        self._shutting_down: bool = False

    async def connect(self) -> bool:
        """Connect to the MQTT broker."""
        self._connected.clear()

        signed_url = await self._aws_auth.create_signed_url(MQTT_ENDPOINT)
        client_id = await self._generate_client_id()

        LOGGER.debug("MQTT Client ID: %s", client_id)
        LOGGER.debug("Connecting to: wss://%s/mqtt", MQTT_ENDPOINT)

        client = mqtt.Client(
            client_id=client_id,
            transport="websockets",
            protocol=MQTTProtocolVersion.MQTTv311,
            callback_api_version=CallbackAPIVersion.VERSION2,
        )
        client._reconnect_on_failure = False  # type: ignore[attr-defined]  # noqa: SLF001
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        client.on_disconnect = self._on_disconnect
        client.on_subscribe = self._on_subscribe

        # Parse the URL to extract path and query
        parsed_url = urllib.parse.urlparse(signed_url)
        path_with_query = f"{parsed_url.path}?{parsed_url.query}"
        websocket_headers = {
            "Host": MQTT_ENDPOINT,
            "Sec-WebSocket-Protocol": "mqtt",
        }
        client.ws_set_options(path=path_with_query, headers=websocket_headers)
        client.username_pw_set(username="?SDK=Android&Version=2.75.0", password=None)
        client.tls_set(
            ca_certs=None,
            certfile=None,
            keyfile=None,
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLS_CLIENT,
        )

        try:
            client.connect(MQTT_ENDPOINT, port=443, keepalive=30)
        except Exception as e:
            LOGGER.error("Failed to connect to MQTT broker: %s", e)
            return False

        client.loop_start()
        self._client = client

        try:
            await asyncio.wait_for(self._connected.wait(), timeout=10.0)
        except TimeoutError:
            LOGGER.error("MQTT connection timeout")
            client.loop_stop()
            self._client = None
            return False

        self._client_id = client_id
        return True

    async def disconnect(self) -> None:
        """Disconnect from the MQTT broker."""
        self._shutting_down = True

        if self._reconnect_task is not None:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
            self._reconnect_task = None

        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None
        self._connected.clear()

    def is_connected(self) -> bool:
        """Check if connected to the MQTT broker."""
        return self._connected.is_set()

    def subscribe(self, topic: str) -> None:
        """Subscribe to an MQTT topic."""
        self._subscribed_topics.add(topic)
        if self._client and self._connected.is_set():
            self._client.subscribe(topic, qos=1)

    @property
    def client_id(self) -> str | None:
        """The current MQTT client ID, or None if not connected."""
        return self._client_id

    def unsubscribe(self, topic: str) -> None:
        """Unsubscribe from an MQTT topic."""
        self._subscribed_topics.discard(topic)
        if self._client and self._connected.is_set():
            self._client.unsubscribe(topic)

    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        """Publish a message to an MQTT topic."""
        if not self._client or not self._connected.is_set():
            LOGGER.warning("Cannot publish, MQTT client not connected")
            return

        payload_json = json.dumps(payload)
        self._client.publish(topic, payload_json, qos=1)

    async def _generate_client_id(self) -> str:
        identity_id = await self._aws_auth.get_cognito_identity_id()
        if not identity_id:
            raise RuntimeError("Failed to get Cognito identity ID")
        return _generate_client_id(identity_id)

    def _on_connect(
        self,
        _client: mqtt.Client,
        _userdata: Any,
        _connect_flags: mqtt.ConnectFlags,
        reason_code: ReasonCode,
        _properties: Properties | None = None,
    ) -> None:
        """Callback when connected to MQTT broker."""
        if reason_code.is_failure:
            LOGGER.error("MQTT connection failed: %s", reason_code)
            return

        self._loop.call_soon_threadsafe(self._resubscribe_and_set_connected)

    def _resubscribe_and_set_connected(self) -> None:
        """Resubscribe to all topics and mark as connected. Runs on the event loop."""
        if not self._client:
            return

        LOGGER.debug(
            "MQTT connected, subscribing %d to topics...", len(self._subscribed_topics)
        )
        for topic in self._subscribed_topics:
            LOGGER.debug("  - %s", topic)
            self._client.subscribe(topic, qos=1)

        self._connected.set()

    def _on_message(
        self, _client: mqtt.Client, _userdata: Any, msg: mqtt.MQTTMessage
    ) -> None:
        """Callback when a message is received."""
        LOGGER.debug("MQTT message on topic: %s", msg.topic)

        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            LOGGER.warning("Failed to decode message: %s", e)
            return

        LOGGER.debug("Payload: %s", json.dumps(payload, indent=2))

        if self._message_callback:
            self._loop.call_soon_threadsafe(self._message_callback, msg.topic, payload)

    def _on_disconnect(
        self,
        _client: mqtt.Client,
        _userdata: Any,
        _disconnect_flags: mqtt.DisconnectFlags,
        reason_code: ReasonCode,
        _properties: Properties | None = None,
    ) -> None:
        """Callback when disconnected from MQTT broker."""
        if reason_code.is_failure:
            LOGGER.warning("MQTT unexpected disconnect: %s", reason_code)
        else:
            LOGGER.debug("MQTT disconnected cleanly")

        self._loop.call_soon_threadsafe(self._connected.clear)

        if reason_code.is_failure:
            self._loop.call_soon_threadsafe(self._schedule_reconnect)

    def _schedule_reconnect(self) -> None:
        """Start a reconnect task if one isn't already running."""
        if self._shutting_down:
            return
        if self._reconnect_task is not None and not self._reconnect_task.done():
            return
        self._reconnect_task = self._loop.create_task(self._reconnect_loop())

    async def _reconnect_loop(self) -> None:
        """Rebuild the MQTT client with fresh auth, using exponential backoff.

        Each attempt drives the full connect() path, which fetches a new
        SigV4-signed websocket URL. The old paho client (if any) is stopped
        before building the new one. `_resubscribe_and_set_connected`
        (called from on_connect) reapplies `self._subscribed_topics` so
        existing subscriptions survive the rebuild.
        """
        delay = RECONNECT_BACKOFF_INITIAL_SECONDS
        while not self._shutting_down:
            LOGGER.warning("MQTT reconnecting in %.1fs", delay)
            try:
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                return

            if self._shutting_down:
                return

            if self._client is not None:
                old = self._client
                self._client = None
                try:
                    old.loop_stop()
                except Exception:
                    LOGGER.debug("Error stopping old MQTT client loop", exc_info=True)

            try:
                ok = await self.connect()
            except asyncio.CancelledError:
                return
            except Exception:
                LOGGER.exception("MQTT reconnect attempt raised")
                ok = False

            if ok:
                LOGGER.warning("MQTT reconnected successfully")
                return

            delay = min(delay * 2 if delay > 0 else 1.0, RECONNECT_BACKOFF_CAP_SECONDS)

    def _on_subscribe(
        self,
        _client: mqtt.Client,
        _userdata: Any,
        mid: int,
        granted_qos: list[ReasonCode],
        _properties: Properties | None = None,
    ) -> None:
        """Callback when subscription is confirmed."""
        LOGGER.debug("MQTT subscription confirmed (mid: %d, QoS: %s)", mid, granted_qos)
