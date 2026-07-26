"""Shared fakes, wire mocks, and manager-builder helpers for AWS IoT tests."""

import json
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import patch

import aiohttp
from aiointercept import aiointercept

from whirlpool.auth import Auth
from whirlpool.awsiot.appliancesmanager import AppliancesManager as AwsAppliancesManager
from whirlpool.awsiot.auth import COGNITO_URL, WHIRLPOOL_COGNITO_URL
from whirlpool.awsiot.things import AWS_IOT_ENDPOINT
from whirlpool.backendselector import BackendSelector

MWO_SAID = "WPR1A00000001"
MWO_MODEL = "KMMC5019JBS"
MWO_CAP_PART = "W11788386"

# Shaped like a real Cognito identity id (`region:uuid`): `Things.list_things`
# derives the thing-group name from the part after the colon.
COGNITO_IDENTITY_ID = "us-east-2:11111111-2222-3333-4444-555555555555"

_THINGS_PAGE_TOKEN = "next-page"

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


def mock_aws_http_api(
    http_mock: aiointercept,
    backend_selector: BackendSelector,
    things: list[dict[str, Any]],
) -> None:
    """Register wire-level mocks for the AWS-side HTTP endpoints."""
    http_mock.post(
        backend_selector.oauth_token_url,
        payload={"access_token": "fake_access_token", "expires_in": 3600},
        repeat=True,
    )
    http_mock.get(
        WHIRLPOOL_COGNITO_URL,
        payload={"identityId": COGNITO_IDENTITY_ID, "token": "fake-cognito-token"},
        repeat=True,
    )
    http_mock.post(
        COGNITO_URL,
        payload={
            "Credentials": {
                "AccessKeyId": "FAKEACCESSKEYID",
                "SecretKey": "fake-secret-key",
                "SessionToken": "fake-session-token",
                "Expiration": time.time() + 3600,
            }
        },
        repeat=True,
    )

    group_name = COGNITO_IDENTITY_ID.split(":")[1]
    things_url = f"https://{AWS_IOT_ENDPOINT}/thing-groups/{group_name}/things"
    thing_names = [thing["thingName"] for thing in things]
    if len(thing_names) > 1:
        # Split into two pages when there is more than one thing to test pagination
        http_mock.get(
            things_url,
            payload={"things": thing_names[:1], "nextToken": _THINGS_PAGE_TOKEN},
            repeat=True,
        )
        http_mock.get(
            f"{things_url}?nextToken={_THINGS_PAGE_TOKEN}",
            payload={"things": thing_names[1:]},
            repeat=True,
        )
    else:
        http_mock.get(things_url, payload={"things": thing_names}, repeat=True)

    for thing in things:
        http_mock.get(
            f"https://{AWS_IOT_ENDPOINT}/things/{thing['thingName']}",
            payload=thing,
            repeat=True,
        )


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
def patch_aws_manager_mqtt(
    mqtt_factory: Callable[..., FakeMqttClient],
) -> Generator[None]:
    """Patch the manager's `MqttClient` internal with a fake."""
    with patch(
        "whirlpool.awsiot.appliancesmanager.MqttClient",
        side_effect=mqtt_factory,
    ):
        yield


async def build_manager_with_things(
    auth: Auth,
    session: aiohttp.ClientSession,
    http_mock: aiointercept,
    backend_selector: BackendSelector,
    things: list[dict[str, Any]],
    capability_replies: dict[str, dict[str, Any] | None],
) -> AwsAppliancesManager:
    """A connected manager over the given things and capability replies."""
    mock_aws_http_api(http_mock, backend_selector, things)
    mqtt_factory = make_mqtt_factory(STATE, capability_replies)
    with patch_aws_manager_mqtt(mqtt_factory):
        manager = AwsAppliancesManager(auth, session, lambda: None)
        await manager.connect()
    return manager


async def build_manager_with_profile(
    auth: Auth,
    session: aiohttp.ClientSession,
    http_mock: aiointercept,
    backend_selector: BackendSelector,
    profile: dict[str, Any],
) -> tuple[AwsAppliancesManager, FakeMqttClient]:
    """A connected manager whose microwave capability reply is `profile`."""
    mock_aws_http_api(http_mock, backend_selector, [THING])
    holder: dict[str, FakeMqttClient] = {}
    mqtt_factory = make_mqtt_factory(STATE, {MWO_CAP_PART: profile}, holder)
    with patch_aws_manager_mqtt(mqtt_factory):
        manager = AwsAppliancesManager(auth, session, lambda: None)
        await manager.connect()
    return manager, holder["client"]
