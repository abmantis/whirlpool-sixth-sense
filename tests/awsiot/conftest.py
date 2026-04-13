import json
from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from whirlpool.types import ApplianceInfo

from . import DATA_DIR

MessageHandler = Callable[[str, dict[str, Any]], Awaitable[None]]
ConnectionHandler = Callable[[], Awaitable[None]]


class FakeMqttClient:
    """In-memory stand-in for whirlpool.awsiot.MqttClient.

    Implements the same public surface the real client exposes so tests
    can drive messages, assert published traffic, and simulate connection
    lifecycle events without touching paho or the network.
    """

    def __init__(self, client_id: str = "fake-identity_deadbeefcafef00d") -> None:
        self._connected: bool = False
        self._client_id: str = client_id
        self.subscriptions: set[str] = set()
        self.published: list[tuple[str, dict[str, Any]]] = []
        self._message_handlers: list[MessageHandler] = []
        self._on_connect_handlers: list[ConnectionHandler] = []
        self._on_disconnect_handlers: list[ConnectionHandler] = []

    # --- lifecycle -------------------------------------------------------

    async def connect(self) -> bool:
        self._connected = True
        for handler in list(self._on_connect_handlers):
            await handler()
        return True

    async def disconnect(self) -> None:
        self._connected = False
        for handler in list(self._on_disconnect_handlers):
            await handler()

    def is_connected(self) -> bool:
        return self._connected

    @property
    def client_id(self) -> str | None:
        return self._client_id if self._connected else None

    # --- pub/sub ---------------------------------------------------------

    async def subscribe(self, topic: str) -> None:
        self.subscriptions.add(topic)

    async def unsubscribe(self, topic: str) -> None:
        self.subscriptions.discard(topic)

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        self.published.append((topic, payload))

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

    # --- test-only driving API ------------------------------------------

    async def inject(self, topic: str, payload: dict[str, Any]) -> None:
        """Fire registered handlers as if a message arrived on `topic`."""
        for handler in list(self._message_handlers):
            await handler(topic, payload)

    async def simulate_disconnect(self) -> None:
        self._connected = False
        for handler in list(self._on_disconnect_handlers):
            await handler()

    async def simulate_reconnect(self) -> None:
        self._connected = True
        for handler in list(self._on_connect_handlers):
            await handler()

    def clear_published(self) -> None:
        self.published.clear()


def _load_json(name: str) -> dict[str, Any]:
    with open(DATA_DIR / name) as f:
        return json.load(f)


@pytest.fixture
def fake_mqtt() -> FakeMqttClient:
    return FakeMqttClient()


@pytest.fixture
def capability_mwo_raw() -> dict[str, Any]:
    return _load_json("capability_mwo.json")


@pytest.fixture
def capability_mwo_no_hood_raw() -> dict[str, Any]:
    return _load_json("capability_mwo_no_hood.json")


@pytest.fixture
def thing_mwo() -> dict[str, Any]:
    return _load_json("thing_mwo.json")


@pytest.fixture
def state_mwo_full() -> dict[str, Any]:
    return _load_json("state_mwo_full.json")


@pytest.fixture
def state_mwo_cooking() -> dict[str, Any]:
    return _load_json("state_mwo_cooking.json")


@pytest.fixture
def appliance_info_mwo(thing_mwo: dict[str, Any]) -> ApplianceInfo:
    return ApplianceInfo(
        said=thing_mwo["thingName"],
        name=bytes.fromhex(thing_mwo["attributes"]["Name"]).decode("utf-8"),
        category=thing_mwo["attributes"]["Category"].lower(),
        model_number=thing_mwo["thingTypeName"],
        serial_number=thing_mwo["attributes"]["Serial"],
    )
