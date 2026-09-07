"""Whirlpool AWS IoT MQTT Client"""

import asyncio
import json
import logging
import secrets
import ssl
import threading
import urllib.parse
from collections.abc import Callable, Coroutine
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion, MQTTProtocolVersion
from paho.mqtt.properties import Properties
from paho.mqtt.reasoncodes import ReasonCode

from .auth import Auth

LOGGER = logging.getLogger(__name__)

MQTT_ENDPOINT = "wt.applianceconnect.net"
CONNECT_TIMEOUT_SECONDS = 10.0
RECONNECT_BACKOFF_INITIAL_SECONDS = 1.0
RECONNECT_BACKOFF_CAP_SECONDS = 30.0


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
        self._connected = threading.Event()
        self._disconnect_called = threading.Event()
        self._subscribed_topics: set[str] = set()
        self._client_id: str | None = None
        self._client_id_suffix: str = secrets.token_hex(8)

        self._loop = asyncio.get_running_loop()
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="whirlpool-mqtt-client"
        )

    def _teardown_client(self) -> None:
        """Stop and disconnect of the current paho client, if any."""
        if self._client is None:
            return
        old = self._client
        self._client = None
        try:
            old.loop_stop()
        except Exception:
            LOGGER.debug("Error stopping MQTT client loop", exc_info=True)
        try:
            old.disconnect()
        except Exception:
            LOGGER.debug("Error disconnecting MQTT client", exc_info=True)

    async def connect(self) -> bool:
        """Connect to the MQTT broker."""
        self._disconnect_called.clear()
        return await self._run_on_worker(self._worker_connect)

    def _worker_connect(self) -> bool:
        """Connect to the MQTT broker. Must be called in the worker thread context."""
        self._connected.clear()
        self._teardown_client()

        signed_url = self._run_on_loop(self._aws_auth.create_signed_url, MQTT_ENDPOINT)
        client_id = self._generate_client_id()

        LOGGER.debug("MQTT Client ID: %s", client_id)
        LOGGER.debug("Connecting to: wss://%s/mqtt", MQTT_ENDPOINT)

        client = mqtt.Client(
            client_id=client_id,
            transport="websockets",
            protocol=MQTTProtocolVersion.MQTTv311,
            callback_api_version=CallbackAPIVersion.VERSION2,
            reconnect_on_failure=False,
        )
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
        except Exception:
            LOGGER.debug("Failed to connect to MQTT broker", exc_info=True)
            return False

        self._client = client
        # TODO: should we just call loop() ourselves, now that we have a worker thread?
        client.loop_start()

        if (
            not self._connected.wait(
                timeout=CONNECT_TIMEOUT_SECONDS
            )  # TODO: will this block if disconnected is called during connect?
            or self._disconnect_called.is_set()
        ):
            LOGGER.debug("MQTT connection timeout or disconnect called during connect")
            self._teardown_client()
            return False

        LOGGER.debug(
            "MQTT connected, subscribing %d to topics...", len(self._subscribed_topics)
        )
        for topic in self._subscribed_topics:
            LOGGER.debug("  - %s", topic)
            self._client.subscribe(topic, qos=1)

        self._client_id = client_id
        return True

    async def disconnect(self) -> None:
        """Disconnect from the MQTT broker and shutdown."""
        self._disconnect_called.set()
        await self._run_on_worker(self._worker_disconnect)
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _worker_disconnect(self) -> None:
        """Disconnect from the MQTT broker.
        Must be called in the worker thread context."""
        self._teardown_client()
        self._connected.clear()
        self._client_id = None

    def is_connected(self) -> bool:
        """Check if connected to the MQTT broker."""
        return self._connected.is_set()

    async def subscribe(self, topic: str) -> None:
        """Subscribe to an MQTT topic."""
        await self._run_on_worker(self._worker_subscribe, topic)

    def _worker_subscribe(self, topic: str) -> None:
        """Subscribe to an MQTT topic. Must be called in the worker thread context."""
        self._subscribed_topics.add(topic)
        if self._client and self._connected.is_set():
            self._client.subscribe(topic, qos=1)

    @property
    def client_id(self) -> str | None:
        """The current MQTT client ID, or None if not connected."""
        return self._client_id

    async def unsubscribe(self, topic: str) -> None:
        """Unsubscribe from an MQTT topic."""
        await self._run_on_worker(self._worker_unsubscribe, topic)

    def _worker_unsubscribe(self, topic: str) -> None:
        """Unsubscribe from an MQTT topic.
        Must be called in the worker thread context."""
        self._subscribed_topics.discard(topic)
        if self._client and self._connected.is_set():
            self._client.unsubscribe(topic)

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        """Publish a message to an MQTT topic."""
        await self._run_on_worker(self._worker_publish, topic, payload)

    def _worker_publish(self, topic: str, payload: dict[str, Any]) -> None:
        """Publish a message to an MQTT topic.
        Must be called in the worker thread context."""
        if not self._client or not self._connected.is_set():
            LOGGER.warning("Cannot publish, MQTT client not connected")
            return

        payload_json = json.dumps(payload)
        self._client.publish(topic, payload_json, qos=1)

    def _generate_client_id(self) -> str:
        identity_id = self._run_on_loop(self._aws_auth.get_cognito_identity_id)
        if not identity_id:
            raise RuntimeError("Failed to get Cognito identity ID")
        return f"{identity_id}_{self._client_id_suffix}"

    def _is_active_client(self, client: mqtt.Client) -> bool:
        return self._client is client

    def _on_connect(
        self,
        client: mqtt.Client,
        _userdata: Any,
        _connect_flags: mqtt.ConnectFlags,
        reason_code: ReasonCode,
        _properties: Properties | None = None,
    ) -> None:
        """Callback when connected to MQTT broker."""
        if not self._is_active_client(client):
            LOGGER.debug("Ignoring on_connect from stale MQTT client")
            return
        if reason_code.is_failure:
            LOGGER.error("MQTT connection failed: %s", reason_code)
            return

        self._connected.set()

    def _on_message(
        self, client: mqtt.Client, _userdata: Any, msg: mqtt.MQTTMessage
    ) -> None:
        """Callback when a message is received."""
        if not self._is_active_client(client):
            LOGGER.debug("Ignoring message from stale MQTT client on %s", msg.topic)
            return
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
        client: mqtt.Client,
        _userdata: Any,
        _disconnect_flags: mqtt.DisconnectFlags,
        reason_code: ReasonCode,
        _properties: Properties | None = None,
    ) -> None:
        """Callback when disconnected from MQTT broker."""
        if not self._is_active_client(client):
            LOGGER.debug("Ignoring on_disconnect from stale MQTT client")
            return
        if reason_code.is_failure:
            LOGGER.warning("MQTT unexpected disconnect: %s", reason_code)
        else:
            LOGGER.debug("MQTT disconnected cleanly")

        was_connected = self._connected.is_set()
        self._connected.clear()

        if reason_code.is_failure and was_connected:
            self._executor.submit(self._worker_reconnect_loop)

    def _worker_reconnect_loop(self) -> None:
        """Retry connecting using exponential backoff."""
        if self._connected.is_set():
            LOGGER.debug("MQTT already connected, skipping reconnect loop")
            return
        delay = RECONNECT_BACKOFF_INITIAL_SECONDS
        while not self._disconnect_called.wait(delay):
            if not self._loop.is_running():
                LOGGER.debug("Event loop stopped, aborting MQTT reconnect loop")
                return
            LOGGER.debug("MQTT reconnecting in %.1fs", delay)

            try:
                if self._worker_connect():
                    LOGGER.info("MQTT reconnected successfully")
                    return
            except Exception as e:
                LOGGER.warning("MQTT reconnect attempt failed: %s", e)
                LOGGER.debug("MQTT reconnect attempt traceback", exc_info=True)

            delay = min(delay * 2, RECONNECT_BACKOFF_CAP_SECONDS)

    def _on_subscribe(
        self,
        client: mqtt.Client,
        _userdata: Any,
        mid: int,
        granted_qos: list[ReasonCode],
        _properties: Properties | None = None,
    ) -> None:
        """Callback when subscription is confirmed."""
        if not self._is_active_client(client):
            LOGGER.debug("Ignoring subscribe ack from stale MQTT client")
            return
        LOGGER.debug("MQTT subscription confirmed (mid: %d, QoS: %s)", mid, granted_qos)

    async def _run_on_worker[*Ts, T](self, func: Callable[[*Ts], T], *args: *Ts) -> T:
        """Run a synchronous function on the worker thread."""
        return await self._loop.run_in_executor(self._executor, func, *args)

    def _run_on_loop[T](
        self,
        coro_func: Callable[..., Coroutine[Any, Any, T]],
        *args: Any,
        timeout: float = 30.0,
    ) -> T:
        """Run a coroutine on the event loop from the worker thread context."""
        if not self._loop.is_running():
            raise RuntimeError(
                f"Event loop is not running, cannot run {coro_func.__qualname__}"
            )
        return asyncio.run_coroutine_threadsafe(coro_func(*args), self._loop).result(
            timeout=timeout
        )
