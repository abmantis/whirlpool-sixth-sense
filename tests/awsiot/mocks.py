"""Shared fakes and wire mocks for AWS IoT tests."""

import asyncio
import json
import threading
import time
from pathlib import Path
from typing import Any

import paho.mqtt.client as mqtt
from aiointercept import aiointercept
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.reasoncodes import ReasonCode

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


class FakePahoClient:
    """Stand-in for `paho.mqtt.client.Client`, attached to a `FakePahoBroker`."""

    def __init__(self, broker: FakePahoBroker, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self._broker = broker
        self.on_connect: Any = None
        self.on_message: Any = None
        self.on_disconnect: Any = None
        self.on_subscribe: Any = None
        self.subscribed: set[str] = set()
        self.loop_stopped = False
        self.disconnected = False

    def ws_set_options(self, **_kwargs: Any) -> None:
        pass

    def username_pw_set(self, **_kwargs: Any) -> None:
        pass

    def tls_set(self, **_kwargs: Any) -> None:
        pass

    def connect(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    def loop_start(self) -> None:
        # The CONNACK comes from a background thread, as from paho's network
        # thread.
        if self._broker.connack:
            threading.Thread(
                target=self.on_connect,
                args=(
                    self,
                    None,
                    mqtt.ConnectFlags(session_present=False),
                    ReasonCode(PacketTypes.CONNACK, "Success"),
                    None,
                ),
                daemon=True,
            ).start()

    def loop_stop(self) -> None:
        self.loop_stopped = True

    def disconnect(self) -> None:
        self.disconnected = True

    def subscribe(self, topic: str, qos: int = 0) -> None:
        self.subscribed.add(topic)

    def unsubscribe(self, topic: str) -> None:
        self.subscribed.discard(topic)

    def publish(self, topic: str, payload: str, qos: int = 0) -> None:
        self._broker.handle_publish(topic, json.loads(payload))

    def fire_disconnect(self, *, is_failure: bool) -> None:
        """Simulate the broker dropping the connection."""
        reason = "Unspecified error" if is_failure else "Normal disconnection"
        self.on_disconnect(
            self,
            None,
            mqtt.DisconnectFlags(is_disconnect_packet_from_server=True),
            ReasonCode(PacketTypes.DISCONNECT, reason),
            None,
        )

    def deliver(
        self, topic: str, payload: dict[str, Any], *, unsolicited: bool = False
    ) -> bool:
        """Hand a message to paho's `on_message` if subscribed to `topic`."""
        if self.disconnected:
            return False
        if not unsolicited and not any(
            mqtt.topic_matches_sub(sub, topic) for sub in self.subscribed
        ):
            return False
        message = mqtt.MQTTMessage(topic=topic.encode())
        message.payload = json.dumps(payload).encode()
        self.on_message(self, None, message)
        return True


class FakePahoBroker:
    """Installed in place of `paho.mqtt.client.Client`: plays the AWS IoT broker
    and the appliances behind it.

    Every paho client `MqttClient` builds attaches here. Publishes are recorded
    and answered the way the cloud would: a `getState` with the appliance's
    entry in `states`, a capability download with the part's entry in
    `capabilities` (`None` sends no reply, for the retry/timeout path).
    """

    def __init__(self) -> None:
        self.clients: list[FakePahoClient] = []
        self.connack = True
        self.published: list[tuple[str, dict[str, Any]]] = []
        self.states: dict[str, dict[str, Any]] = {}
        self.capabilities: dict[str, dict[str, Any] | None] = {}

    def __call__(self, **kwargs: Any) -> FakePahoClient:
        client = FakePahoClient(self, **kwargs)
        self.clients.append(client)
        return client

    @property
    def client_id(self) -> str:
        """The MQTT client ID of the latest paho client."""
        return self.clients[-1].kwargs["client_id"]

    @property
    def subscribed_topics(self) -> set[str]:
        """The topics the latest paho client is subscribed to."""
        return self.clients[-1].subscribed

    async def inject(
        self, topic: str, payload: dict[str, Any], *, unsolicited: bool = False
    ) -> None:
        """Deliver an incoming message and let the event loop process it.

        `unsolicited` delivers it to the latest client even when no client is
        subscribed to `topic`, as a broker never would, to exercise defensive
        routing.
        """
        if unsolicited:
            delivered = self.clients[-1].deliver(topic, payload, unsolicited=True)
        else:
            delivered = self._deliver(topic, payload)
        assert delivered, f"No client subscribed to {topic}"
        # `MqttClient` hands messages to the event loop with call_soon_threadsafe.
        await asyncio.sleep(0)

    def handle_publish(self, topic: str, payload: dict[str, Any]) -> None:
        self.published.append((topic, payload))
        parts = topic.split("/")
        # cmd/{model}/{said}/request/{client_id}
        if (
            len(parts) == 5
            and parts[0] == "cmd"
            and parts[3] == "request"
            and payload.get("payload", {}).get("command") == "getState"
            and (state := self.states.get(parts[2])) is not None
        ):
            self._deliver(
                f"cmd/{parts[1]}/{parts[2]}/response/{parts[4]}",
                {
                    "requestId": payload.get("requestId"),
                    "response": "accepted",
                    "payload": state,
                },
            )
        # api/capability/download/{model}/{said}
        if topic.startswith("api/capability/download/"):
            reply = self.capabilities.get(payload.get("capabilityPartNumber", ""))
            if reply is not None:
                self._deliver(f"{topic}/response", reply)

    def _deliver(self, topic: str, payload: dict[str, Any]) -> bool:
        # A list, not a generator: every subscribed client gets the message.
        delivered = [client.deliver(topic, payload) for client in self.clients]
        return any(delivered)


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


def mock_aws_api(
    http_mock: aiointercept,
    backend_selector: BackendSelector,
    broker: FakePahoBroker,
    things: list[dict[str, Any]],
    capabilities: dict[str, dict[str, Any] | None],
    state: dict[str, Any] = STATE,
) -> None:
    """Mock the whole AWS side: HTTP endpoints at the wire, and broker replies
    with `state` for every thing and `capabilities` for capability downloads."""
    mock_aws_http_api(http_mock, backend_selector, things)
    for thing in things:
        broker.states[thing["thingName"]] = state
    broker.capabilities.update(capabilities)
