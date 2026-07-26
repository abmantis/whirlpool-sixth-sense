"""Shared fakes and manager-builder helpers for AWS IoT tests."""

import json
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import aiohttp

from whirlpool.auth import Auth
from whirlpool.awsiot.appliancesmanager import AppliancesManager as AwsAppliancesManager

MWO_SAID = "WPR1A00000001"
MWO_MODEL = "KMMC5019JBS"
MWO_CAP_PART = "W11788386"

_DATA_DIR = Path(__file__).parent.parent / "data" / "awsiot"

MWO_CAPABILITY_PROFILE: dict[str, Any] = json.loads(
    (_DATA_DIR / "capability_mwo.json").read_text()
)

THING: dict[str, Any] = json.loads((_DATA_DIR / "microwave_thing.json").read_text())
STATE: dict[str, Any] = json.loads((_DATA_DIR / "microwave_state.json").read_text())


class FakeMqttClient:
    """In-memory MQTT stand-in.

    Captures `publish()` calls and lets tests `inject()` incoming messages
    through the same callback that `AwsAppliancesManager` registers on the
    real `MqttClient`. Automatically replies to a published `getState`
    with a preconfigured payload so that `Appliance.fetch_data()` resolves.
    """

    def __init__(
        self,
        _aws_auth: Any = None,
        message_callback: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        self._message_callback = message_callback
        self.client_id: str | None = "fake-client-id"
        self.subscribed_topics: set[str] = set()
        self.published: list[tuple[str, dict[str, Any]]] = []
        self._connected = True
        self._getstate_reply: dict[str, Any] | None = None
        self._capability_replies: dict[str, dict[str, Any] | None] = {}

    def set_getstate_reply(self, payload: dict[str, Any]) -> None:
        self._getstate_reply = payload

    def set_capability_reply(
        self, part_number: str, payload: dict[str, Any] | None
    ) -> None:
        """Configure the inline profile JSON returned for a capability request.

        Pass `None` to simulate no response (retry/timeout path).
        """
        self._capability_replies[part_number] = payload

    async def connect(self) -> bool:
        return True

    async def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def subscribe(self, topic: str) -> None:
        self.subscribed_topics.add(topic)

    def unsubscribe(self, topic: str) -> None:
        self.subscribed_topics.discard(topic)

    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        self.published.append((topic, payload))
        cmd = payload.get("payload", {}).get("command")
        if cmd == "getState" and self._getstate_reply is not None:
            parts = topic.split("/")
            # cmd/{model}/{said}/request/{client_id}
            if len(parts) >= 5 and parts[0] == "cmd" and parts[3] == "request":
                model, said, cid = parts[1], parts[2], parts[4]
                response_topic = f"cmd/{model}/{said}/response/{cid}"
                self.inject(response_topic, {"payload": self._getstate_reply})
        # Capability download: api/capability/download/{model}/{said}
        if topic.startswith("api/capability/download/"):
            part = payload.get("capabilityPartNumber", "")
            reply = self._capability_replies.get(part)
            if reply is not None:
                self.inject(f"{topic}/response", reply)

    def inject(self, topic: str, payload: dict[str, Any]) -> None:
        if self._message_callback is not None:
            self._message_callback(topic, payload)


class FakeThings:
    """Fake `Things` API returning a configurable list of things.

    Use `with_things()` to build a class configured with a specific list,
    suitable for patching `whirlpool.awsiot.appliancesmanager.Things`.
    """

    things: list[dict[str, Any]] = []

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def list_things(self) -> list[dict[str, Any]]:
        return self.things

    @classmethod
    def with_things(cls, things: list[dict[str, Any]]) -> type[FakeThings]:
        return cast("type[FakeThings]", type(cls.__name__, (cls,), {"things": things}))


def make_mqtt_factory(
    getstate_reply: dict[str, Any],
    capability_replies: dict[str, dict[str, Any] | None],
    holder: dict[str, FakeMqttClient] | None = None,
) -> Callable[..., FakeMqttClient]:
    """Build a `MqttClient` factory preloaded with canned replies.

    Every created `FakeMqttClient` replies to `getState` with
    `getstate_reply` and to capability downloads with `capability_replies`.
    When `holder` is given, the created client is stored under
    `holder["client"]` so tests can reach it after the manager connects.
    """

    def _factory(
        aws_auth: Any,
        message_callback: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> FakeMqttClient:
        fake = FakeMqttClient(aws_auth, message_callback)
        fake.set_getstate_reply(getstate_reply)
        for part, reply in capability_replies.items():
            fake.set_capability_reply(part, reply)
        if holder is not None:
            holder["client"] = fake
        return fake

    return _factory


@contextmanager
def patch_aws_manager_internals(
    mqtt_factory: Callable[..., FakeMqttClient],
    things: list[dict[str, Any]],
) -> Generator[None]:
    """Patch the manager's `MqttClient` and `Things` internals with fakes."""
    with (
        patch(
            "whirlpool.awsiot.appliancesmanager.MqttClient",
            side_effect=mqtt_factory,
        ),
        patch(
            "whirlpool.awsiot.appliancesmanager.Things",
            FakeThings.with_things(things),
        ),
    ):
        yield


async def build_manager_with_things(
    auth: Auth,
    session: aiohttp.ClientSession,
    things: list[dict[str, Any]],
    capability_replies: dict[str, dict[str, Any] | None],
) -> AwsAppliancesManager:
    """A connected manager over the given things and capability replies."""
    mqtt_factory = make_mqtt_factory(STATE, capability_replies)
    with patch_aws_manager_internals(mqtt_factory, things):
        manager = AwsAppliancesManager(auth, session, lambda: None)
        await manager.connect()
    return manager


async def build_manager_with_profile(
    auth: Auth,
    session: aiohttp.ClientSession,
    profile: dict[str, Any],
) -> tuple[AwsAppliancesManager, FakeMqttClient]:
    """A connected manager whose microwave capability reply is `profile`."""
    holder: dict[str, FakeMqttClient] = {}
    mqtt_factory = make_mqtt_factory(STATE, {MWO_CAP_PART: profile}, holder)
    with patch_aws_manager_internals(mqtt_factory, [THING]):
        manager = AwsAppliancesManager(auth, session, lambda: None)
        await manager.connect()
    return manager, holder["client"]
