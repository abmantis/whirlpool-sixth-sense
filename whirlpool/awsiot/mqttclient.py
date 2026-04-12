"""Whirlpool AWS IoT MQTT Client (async-safe)."""

import asyncio
import json
import logging
import secrets
import ssl
import urllib.parse
from collections.abc import Awaitable, Callable
from typing import Any

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion, MQTTProtocolVersion
from paho.mqtt.properties import Properties
from paho.mqtt.reasoncodes import ReasonCode

from .auth import Auth

LOGGER = logging.getLogger(__name__)

MQTT_ENDPOINT = "wt.applianceconnect.net"
CONNECT_TIMEOUT_SECONDS = 10.0
RECONNECT_BACKOFF_CAP_SECONDS = 30.0

MessageHandler = Callable[[str, dict[str, Any]], Awaitable[None]]
ConnectionHandler = Callable[[], Awaitable[None]]


def _generate_client_id(identity_id: str) -> str:
    """Generate a client ID in the format used by the Android app."""
    random_suffix = secrets.token_hex(8)  # 16 hex chars
    return f"{identity_id}_{random_suffix}"


class MqttClient:
    """Async-safe MQTT client for Whirlpool AWS IoT.

    All public methods are coroutines or sync accessors. Paho runs in its
    own network thread; incoming messages are marshalled onto the asyncio
    loop through a queue, and handlers never run on the paho thread.
    """

    def __init__(self, aws_auth: Auth) -> None:
        self._aws_auth = aws_auth
        self._client: mqtt.Client | None = None
        self._connected = asyncio.Event()
        self._subscribed_topics: set[str] = set()
        self._client_id: str | None = None

        self._loop = asyncio.get_running_loop()
        self._incoming: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()
        self._dispatch_task: asyncio.Task[None] | None = None

        self._message_handlers: list[MessageHandler] = []
        self._on_connect_handlers: list[ConnectionHandler] = []
        self._on_disconnect_handlers: list[ConnectionHandler] = []

    # --- lifecycle -------------------------------------------------------

    async def connect(self) -> bool:
        signed_url = await self._aws_auth.create_signed_url(MQTT_ENDPOINT)
        client_id = await self._generate_client_id_async()

        LOGGER.debug("MQTT Client ID: %s", client_id)
        LOGGER.debug("Connecting to wss://%s/mqtt", MQTT_ENDPOINT)

        client = mqtt.Client(
            client_id=client_id,
            transport="websockets",
            protocol=MQTTProtocolVersion.MQTTv311,
            callback_api_version=CallbackAPIVersion.VERSION2,
        )
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        client.on_disconnect = self._on_disconnect
        client.on_subscribe = self._on_subscribe

        parsed_url = urllib.parse.urlparse(signed_url)
        path_with_query = f"{parsed_url.path}?{parsed_url.query}"
        client.ws_set_options(
            path=path_with_query,
            headers={
                "Host": MQTT_ENDPOINT,
                "Sec-WebSocket-Protocol": "mqtt",
            },
        )
        client.username_pw_set(username="?SDK=Android&Version=2.75.0", password=None)
        client.tls_set(
            ca_certs=None,
            certfile=None,
            keyfile=None,
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLS_CLIENT,
        )

        try:
            await self._loop.run_in_executor(
                None, lambda: client.connect(MQTT_ENDPOINT, port=443, keepalive=30)
            )
        except Exception as e:
            LOGGER.error("Failed to connect to MQTT broker: %s", e)
            return False

        client.loop_start()
        self._client = client

        try:
            await asyncio.wait_for(
                self._connected.wait(), timeout=CONNECT_TIMEOUT_SECONDS
            )
        except TimeoutError:
            LOGGER.error("MQTT connection timeout")
            client.loop_stop()
            self._client = None
            return False

        self._client_id = client_id
        self._dispatch_task = self._loop.create_task(self._dispatch_loop())
        return True

    async def disconnect(self) -> None:
        if self._dispatch_task is not None:
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass
            self._dispatch_task = None

        if self._client is not None:
            client = self._client
            await self._loop.run_in_executor(None, client.loop_stop)
            await self._loop.run_in_executor(None, client.disconnect)
            self._client = None

        self._connected.clear()
        self._client_id = None

    def is_connected(self) -> bool:
        return self._connected.is_set()

    @property
    def client_id(self) -> str | None:
        return self._client_id

    # --- pub/sub ---------------------------------------------------------

    async def subscribe(self, topic: str) -> None:
        self._subscribed_topics.add(topic)
        if self._client is not None and self._connected.is_set():
            client = self._client
            await self._loop.run_in_executor(
                None, lambda: client.subscribe(topic, qos=1)
            )

    async def unsubscribe(self, topic: str) -> None:
        self._subscribed_topics.discard(topic)
        if self._client is not None and self._connected.is_set():
            client = self._client
            await self._loop.run_in_executor(None, lambda: client.unsubscribe(topic))

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        if self._client is None or not self._connected.is_set():
            LOGGER.warning("Cannot publish, MQTT client not connected")
            return
        client = self._client
        body = json.dumps(payload)
        await self._loop.run_in_executor(
            None, lambda: client.publish(topic, body, qos=1)
        )

    # --- handler registration -------------------------------------------

    def add_message_handler(self, handler: MessageHandler) -> None:
        self._message_handlers.append(handler)

    def remove_message_handler(self, handler: MessageHandler) -> None:
        try:
            self._message_handlers.remove(handler)
        except ValueError:
            pass

    def add_connection_handler(
        self,
        on_connect: ConnectionHandler | None = None,
        on_disconnect: ConnectionHandler | None = None,
    ) -> None:
        if on_connect is not None:
            self._on_connect_handlers.append(on_connect)
        if on_disconnect is not None:
            self._on_disconnect_handlers.append(on_disconnect)

    # --- internals -------------------------------------------------------

    async def _generate_client_id_async(self) -> str:
        identity_id = await self._aws_auth.get_cognito_identity_id()
        if not identity_id:
            raise RuntimeError("Failed to get Cognito identity ID")
        return _generate_client_id(identity_id)

    async def _dispatch_loop(self) -> None:
        while True:
            topic, payload = await self._incoming.get()
            for handler in list(self._message_handlers):
                try:
                    await handler(topic, payload)
                except Exception:
                    LOGGER.exception(
                        "Message handler raised for topic %s", topic
                    )

    def _on_connect(
        self,
        _client: mqtt.Client,
        _userdata: Any,
        _connect_flags: mqtt.ConnectFlags,
        reason_code: ReasonCode,
        _properties: Properties | None = None,
    ) -> None:
        if reason_code.is_failure:
            LOGGER.error("MQTT connection failed: %s", reason_code)
            return

        self._loop.call_soon_threadsafe(self._resubscribe_and_set_connected)

    def _resubscribe_and_set_connected(self) -> None:
        """Resubscribe to all topics and mark as connected. Runs on the event loop."""
        if not self._client:
            return

        LOGGER.debug(
            "MQTT connected, resubscribing %d topics", len(self._subscribed_topics)
        )
        for topic in self._subscribed_topics:
            LOGGER.debug("  - %s", topic)
            self._client.subscribe(topic, qos=1)

        self._connected.set()
        self._fire_on_connect_handlers()

    def _fire_on_connect_handlers(self) -> None:
        for handler in list(self._on_connect_handlers):
            self._loop.create_task(self._run_connection_handler(handler))

    def _fire_on_disconnect_handlers(self) -> None:
        for handler in list(self._on_disconnect_handlers):
            self._loop.create_task(self._run_connection_handler(handler))

    async def _run_connection_handler(self, handler: ConnectionHandler) -> None:
        try:
            await handler()
        except Exception:
            LOGGER.exception("Connection handler raised")

    def _on_message(
        self, _client: mqtt.Client, _userdata: Any, msg: mqtt.MQTTMessage
    ) -> None:
        # Runs on paho's network thread. Must NOT touch asyncio state
        # directly — marshal onto the event loop.
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            LOGGER.warning("Failed to decode MQTT message on %s: %s", msg.topic, e)
            return

        topic = msg.topic
        self._loop.call_soon_threadsafe(self._incoming.put_nowait, (topic, payload))

    def _on_disconnect(
        self,
        _client: mqtt.Client,
        _userdata: Any,
        _disconnect_flags: mqtt.DisconnectFlags,
        reason_code: ReasonCode,
        _properties: Properties | None = None,
    ) -> None:
        if reason_code.is_failure:
            LOGGER.warning("MQTT unexpected disconnect: %s", reason_code)
        else:
            LOGGER.debug("MQTT disconnected cleanly")

        self._loop.call_soon_threadsafe(self._connected.clear)
        self._loop.call_soon_threadsafe(self._fire_on_disconnect_handlers)

    def _on_subscribe(
        self,
        _client: mqtt.Client,
        _userdata: Any,
        mid: int,
        granted_qos: list[ReasonCode],
        _properties: Properties | None = None,
    ) -> None:
        LOGGER.debug(
            "MQTT subscription confirmed (mid=%d, qos=%s)", mid, granted_qos
        )
