"""Integration tests for the AWS IoT Microwave class.

Rather than driving the Microwave's internal state directly, these tests
construct the real `AwsAppliancesManager` with a fake MQTT client and a
fake `Things` API. State is exchanged as MQTT messages (initial getState
reply, state-update deltas, command publishes), so the test boundary is
the wire contract that abmantis's review asked for.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from typing import Any
from unittest.mock import patch

import aiohttp
import pytest_asyncio

from whirlpool.auth import Auth
from whirlpool.awsiot.appliancesmanager import AppliancesManager as AwsAppliancesManager
from whirlpool.awsiot.microwave import Microwave
from whirlpool.microwave import (
    HoodFanSpeed,
    HoodLightColor,
    HoodLightLevel,
    MicrowaveCavityState,
    MicrowaveDoorStatus,
)

MWO_SAID = "WPR1A00000001"
MWO_MODEL = "KMMC5019JBS"

THING = {
    "thingName": MWO_SAID,
    "thingTypeName": MWO_MODEL,
    "attributes": {
        "Name": b"My Microwave".hex(),
        "Category": "Cooking",
        "Serial": "D1",
    },
}

STATE: dict[str, Any] = {
    "primaryCavity": {
        "cavityState": "idle",
        "doorStatus": "closed",
        "doorLockStatus": "unlocked",
        "cavityLight": False,
        "mwoPowerLevel": 0,
        "ovenDisplayTemperature": 22.5,
        "turnTable": "on",
        "recipeId": "",
        "recipeExecutionState": "idle",
        "cookTimer": {"state": "stopped", "time": 0},
    },
    "hoodFan": {"userFanSpeed": "off"},
    "hoodLight": "med",
    "hoodLightColor": "warmWhite",
    "temperatureUnit": "F",
    "remoteStartEnable": True,
    "hmiControlLockout": False,
    "quietMode": False,
    "sabbathMode": False,
}


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

    def set_getstate_reply(self, payload: dict[str, Any]) -> None:
        self._getstate_reply = payload

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

    def inject(self, topic: str, payload: dict[str, Any]) -> None:
        if self._message_callback is not None:
            self._message_callback(topic, payload)


class _FakeThings:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def list_things(self) -> list[dict[str, Any]]:
        return [THING]


@pytest_asyncio.fixture
async def aws_manager(
    auth: Auth,
    client_session_fixture: aiohttp.ClientSession,
) -> AsyncGenerator[tuple[AwsAppliancesManager, FakeMqttClient]]:
    """An AwsAppliancesManager connected to a fake MQTT + fake Things API."""

    fake_mqtt_holder: dict[str, FakeMqttClient] = {}

    def _mqtt_factory(
        aws_auth: Any,
        message_callback: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> FakeMqttClient:
        fake = FakeMqttClient(aws_auth, message_callback)
        fake.set_getstate_reply(STATE)
        fake_mqtt_holder["client"] = fake
        return fake

    with (
        patch(
            "whirlpool.awsiot.appliancesmanager.MqttClient",
            side_effect=_mqtt_factory,
        ),
        patch(
            "whirlpool.awsiot.appliancesmanager.Things",
            _FakeThings,
        ),
    ):
        manager = AwsAppliancesManager(auth, client_session_fixture, lambda: None)
        ok = await manager.connect()
        assert ok is True
        yield manager, fake_mqtt_holder["client"]


async def test_cooking_category_registers_microwave(
    aws_manager: tuple[AwsAppliancesManager, FakeMqttClient],
) -> None:
    manager, _ = aws_manager
    assert len(manager.microwaves) == 1
    mwo = manager.microwaves[0]
    assert isinstance(mwo, Microwave)
    assert mwo.said == MWO_SAID
    assert mwo.name == "My Microwave"
    # Microwaves should not also appear under ovens.
    assert manager.ovens == []


async def test_subscribes_to_expected_topics(
    aws_manager: tuple[AwsAppliancesManager, FakeMqttClient],
) -> None:
    _, fake_mqtt = aws_manager
    cid = fake_mqtt.client_id
    assert {
        f"cmd/{MWO_MODEL}/{MWO_SAID}/response/{cid}",
        f"dt/{MWO_MODEL}/{MWO_SAID}/state/update",
        f"$aws/events/presence/connected/{MWO_SAID}",
        f"$aws/events/presence/disconnected/{MWO_SAID}",
    }.issubset(fake_mqtt.subscribed_topics)


async def test_initial_state_populates_getters(
    aws_manager: tuple[AwsAppliancesManager, FakeMqttClient],
) -> None:
    manager, _ = aws_manager
    mwo = manager.microwaves[0]

    assert mwo.get_cavity_state() == MicrowaveCavityState.Idle
    assert mwo.get_door_status() == MicrowaveDoorStatus.Closed
    assert mwo.get_door_locked() is False
    assert mwo.get_cavity_light() is False
    assert mwo.get_display_temperature() == 22.5
    assert mwo.get_display_temperature_unit() == "F"
    assert mwo.get_turntable_enabled() is True
    assert mwo.get_active_recipe_id() is None
    assert mwo.get_recipe_execution_state() == "idle"
    assert mwo.get_mwo_power_level() == 0
    assert mwo.get_cook_timer_state() == "stopped"
    assert mwo.get_cook_timer_total_seconds() == 0
    assert mwo.get_cook_timer_time_complete() is None
    assert mwo.get_hood_fan_speed() == HoodFanSpeed.Off
    assert mwo.get_hood_light_level() == HoodLightLevel.Medium
    assert mwo.get_hood_light_color() == HoodLightColor.WarmWhite
    assert mwo.get_remote_start_enabled() is True
    assert mwo.get_control_locked() is False
    assert mwo.get_quiet_mode() is False
    assert mwo.get_sabbath_mode() is False


async def test_missing_fields_return_none(
    auth: Auth,
    client_session_fixture: aiohttp.ClientSession,
) -> None:
    """An appliance whose state only has a few fields shouldn't crash getters."""

    def _mqtt_factory(
        aws_auth: Any,
        message_callback: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> FakeMqttClient:
        fake = FakeMqttClient(aws_auth, message_callback)
        fake.set_getstate_reply({"primaryCavity": {"cavityState": "idle"}})
        return fake

    with (
        patch(
            "whirlpool.awsiot.appliancesmanager.MqttClient",
            side_effect=_mqtt_factory,
        ),
        patch(
            "whirlpool.awsiot.appliancesmanager.Things",
            _FakeThings,
        ),
    ):
        manager = AwsAppliancesManager(auth, client_session_fixture, lambda: None)
        await manager.connect()

    mwo = manager.microwaves[0]
    assert mwo.get_cavity_state() == MicrowaveCavityState.Idle
    assert mwo.get_door_status() is None
    assert mwo.get_door_locked() is None
    assert mwo.get_display_temperature_unit() is None
    assert mwo.get_turntable_enabled() is None
    assert mwo.get_cook_timer_time_complete() is None
    assert mwo.get_hood_fan_speed() is None
    assert mwo.get_hood_light_level() is None


async def test_state_update_reflected_via_mqtt_injection(
    aws_manager: tuple[AwsAppliancesManager, FakeMqttClient],
) -> None:
    manager, fake_mqtt = aws_manager
    mwo = manager.microwaves[0]

    new_state = {**STATE}
    new_state["primaryCavity"] = {
        **STATE["primaryCavity"],
        "cavityState": "cooking",
        "cavityLight": True,
    }
    fake_mqtt.inject(
        f"dt/{MWO_MODEL}/{MWO_SAID}/state/update", new_state
    )

    assert mwo.get_cavity_state() == MicrowaveCavityState.Cooking
    assert mwo.get_cavity_light() is True


async def test_attr_callback_fires_on_state_update(
    aws_manager: tuple[AwsAppliancesManager, FakeMqttClient],
) -> None:
    manager, fake_mqtt = aws_manager
    mwo = manager.microwaves[0]
    calls: list[int] = []
    mwo.register_attr_callback(lambda: calls.append(1))

    fake_mqtt.inject(
        f"dt/{MWO_MODEL}/{MWO_SAID}/state/update", STATE
    )
    assert calls == [1]


async def test_set_cavity_light_publishes_expected_command(
    aws_manager: tuple[AwsAppliancesManager, FakeMqttClient],
) -> None:
    manager, fake_mqtt = aws_manager
    mwo = manager.microwaves[0]

    before = len(fake_mqtt.published)
    ok = await mwo.set_cavity_light(True)
    assert ok is True

    assert len(fake_mqtt.published) == before + 1
    topic, payload = fake_mqtt.published[-1]
    assert topic == (
        f"cmd/{MWO_MODEL}/{MWO_SAID}/request/{fake_mqtt.client_id}"
    )
    assert payload["payload"]["addressee"] == "primaryCavity"
    assert payload["payload"]["command"] == "set"
    assert payload["payload"]["cavityLight"] is True


async def test_unknown_cavity_state_maps_to_none(
    aws_manager: tuple[AwsAppliancesManager, FakeMqttClient],
) -> None:
    manager, fake_mqtt = aws_manager
    mwo = manager.microwaves[0]

    fake_mqtt.inject(
        f"dt/{MWO_MODEL}/{MWO_SAID}/state/update",
        {**STATE, "primaryCavity": {**STATE["primaryCavity"], "cavityState": "bogus"}},
    )
    assert mwo.get_cavity_state() is None


async def test_cook_timer_time_complete_returns_timestamp(
    aws_manager: tuple[AwsAppliancesManager, FakeMqttClient],
) -> None:
    manager, fake_mqtt = aws_manager
    mwo = manager.microwaves[0]

    fake_mqtt.inject(
        f"dt/{MWO_MODEL}/{MWO_SAID}/state/update",
        {
            **STATE,
            "primaryCavity": {
                **STATE["primaryCavity"],
                "cookTimer": {
                    **STATE["primaryCavity"]["cookTimer"],
                    "timeComplete": 1_776_101_159,
                },
            },
        },
    )
    assert mwo.get_cook_timer_time_complete() == 1_776_101_159
