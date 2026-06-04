"""Integration tests for the AWS IoT Microwave class.

Rather than driving the Microwave's internal state directly, these tests
construct the real `AwsAppliancesManager` with a fake MQTT client and a
fake `Things` API. State is exchanged as MQTT messages (initial getState
reply, state-update deltas, command publishes), so the test boundary is
the wire contract that abmantis's review asked for.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator, Callable
from pathlib import Path
from typing import Any
from unittest.mock import patch

import aiohttp
import pytest
import pytest_asyncio

from whirlpool.auth import Auth
from whirlpool.awsiot.appliancesmanager import AppliancesManager as AwsAppliancesManager
from whirlpool.awsiot.capabilities import CapabilityProfile, parse_capability_profile
from whirlpool.awsiot.microwave import Microwave
from whirlpool.microwave import (
    HoodFanSpeed,
    HoodLightColor,
    HoodLightLevel,
    MicrowaveCavityState,
    MicrowaveDoorStatus,
)
from whirlpool.types import ApplianceInfo

MWO_SAID = "WPR1A00000001"
MWO_MODEL = "KMMC5019JBS"
MWO_CAP_PART = "W11043387"

MWO_CAPABILITY_PROFILE: dict[str, Any] = {
    "capabilityPartNumber": MWO_CAP_PART,
    "features": ["microwaveOven", "hoodFan", "hoodLight", "hoodLightColor"],
    "addressees": {
        "primaryCavity": ["set"],
        "hoodFan": ["set"],
        "hoodLight": ["set"],
        "hoodLightColor": ["set"],
    },
}

THING = {
    "thingName": MWO_SAID,
    "thingTypeName": MWO_MODEL,
    "attributes": {
        "Name": b"My Microwave".hex(),
        "Category": "Cooking",
        "Serial": "D1",
        "CapabilityPartNumber": MWO_CAP_PART,
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


class _FakeThings:
    things: list[dict[str, Any]] = [THING]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def list_things(self) -> list[dict[str, Any]]:
        return self.things


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
        fake.set_capability_reply(MWO_CAP_PART, MWO_CAPABILITY_PROFILE)
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
        fake.set_capability_reply(MWO_CAP_PART, MWO_CAPABILITY_PROFILE)
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


async def test_get_online_is_none_before_any_presence_event(
    aws_manager: tuple[AwsAppliancesManager, FakeMqttClient],
) -> None:
    manager, _ = aws_manager
    mwo = manager.microwaves[0]
    assert mwo.get_online() is None


@pytest.mark.parametrize(
    ("events", "expected_online", "expected_callback_states"),
    (
        pytest.param(("connected",), True, [True], id="connected"),
        pytest.param(
            ("connected", "disconnected"),
            False,
            [True, False],
            id="disconnected",
        ),
        pytest.param(
            ("connected", "connected", "disconnected", "disconnected"),
            False,
            [True, False],
            id="unchanged-events",
        ),
    ),
)
async def test_presence_events_update_online_and_fire_callback_on_changes(
    aws_manager: tuple[AwsAppliancesManager, FakeMqttClient],
    events: tuple[str, ...],
    expected_online: bool,
    expected_callback_states: list[bool],
) -> None:
    manager, fake_mqtt = aws_manager
    mwo = manager.microwaves[0]
    calls: list[bool | None] = []
    mwo.register_attr_callback(lambda: calls.append(mwo.get_online()))

    for timestamp, event in enumerate(events, start=1):
        fake_mqtt.inject(
            f"$aws/events/presence/{event}/{MWO_SAID}",
            {"eventType": event, "clientId": "device", "timestamp": timestamp},
        )

    assert mwo.get_online() is expected_online
    assert calls == expected_callback_states


async def test_presence_for_unknown_said_is_ignored(
    aws_manager: tuple[AwsAppliancesManager, FakeMqttClient],
) -> None:
    manager, fake_mqtt = aws_manager
    mwo = manager.microwaves[0]

    fake_mqtt.inject(
        "$aws/events/presence/connected/UNKNOWN_SAID",
        {"eventType": "connected", "clientId": "device", "timestamp": 1},
    )
    assert mwo.get_online() is None


async def test_capability_profile_exposed_on_appliance(
    aws_manager: tuple[AwsAppliancesManager, FakeMqttClient],
) -> None:
    """The profile should be attached so callers can gate further setters."""
    manager, _ = aws_manager
    mwo = manager.microwaves[0]
    assert mwo.capability_profile.part_number == MWO_CAP_PART
    assert mwo.capability_profile.has_feature("microwaveOven")
    assert mwo.capability_profile.has_addressee("hoodFan")


async def _build_manager_with_things(
    auth: Auth,
    session: aiohttp.ClientSession,
    things: list[dict[str, Any]],
    capability_replies: dict[str, dict[str, Any] | None],
) -> AwsAppliancesManager:
    def _mqtt_factory(
        aws_auth: Any,
        message_callback: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> FakeMqttClient:
        fake = FakeMqttClient(aws_auth, message_callback)
        fake.set_getstate_reply(STATE)
        for part, reply in capability_replies.items():
            fake.set_capability_reply(part, reply)
        return fake

    class _Things:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def list_things(self) -> list[dict[str, Any]]:
            return things

    with (
        patch(
            "whirlpool.awsiot.appliancesmanager.MqttClient",
            side_effect=_mqtt_factory,
        ),
        patch("whirlpool.awsiot.appliancesmanager.Things", _Things),
    ):
        manager = AwsAppliancesManager(auth, session, lambda: None)
        await manager.connect()
    return manager


async def test_cooking_without_microwave_feature_routes_to_oven(
    auth: Auth,
    client_session_fixture: aiohttp.ClientSession,
) -> None:
    oven_part = "W99999999"
    oven_profile = {
        "capabilityPartNumber": oven_part,
        "features": ["oven"],
        "addressees": {"primaryCavity": ["set"]},
    }
    oven_thing = {
        **THING,
        "attributes": {**THING["attributes"], "CapabilityPartNumber": oven_part},
    }

    manager = await _build_manager_with_things(
        auth,
        client_session_fixture,
        [oven_thing],
        {oven_part: oven_profile},
    )
    assert manager.microwaves == []
    assert len(manager.ovens) == 1


async def test_missing_capability_part_number_skips_appliance(
    auth: Auth,
    client_session_fixture: aiohttp.ClientSession,
) -> None:
    attrs = {
        k: v for k, v in THING["attributes"].items() if k != "CapabilityPartNumber"
    }
    bad_thing = {**THING, "attributes": attrs}

    manager = await _build_manager_with_things(
        auth, client_session_fixture, [bad_thing], {}
    )
    assert manager.all_appliances == {}


async def test_capability_download_failure_skips_appliance(
    auth: Auth,
    client_session_fixture: aiohttp.ClientSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Shrink the real 10s-per-attempt timeout so the retry path runs fast.
    from whirlpool.awsiot import capabilities as cap_mod

    monkeypatch.setattr(cap_mod, "CAPABILITY_DOWNLOAD_TIMEOUT", 0.01)
    monkeypatch.setattr(cap_mod, "CAPABILITY_DOWNLOAD_RETRIES", 2)

    manager = await _build_manager_with_things(
        auth,
        client_session_fixture,
        [THING],
        {MWO_CAP_PART: None},  # no reply → timeout → skip
    )
    assert manager.all_appliances == {}


async def test_set_hood_fan_speed_publishes_when_supported(
    aws_manager: tuple[AwsAppliancesManager, FakeMqttClient],
) -> None:
    manager, fake_mqtt = aws_manager
    mwo = manager.microwaves[0]
    before = len(fake_mqtt.published)
    ok = await mwo.set_hood_fan_speed(HoodFanSpeed.High)
    assert ok is True
    assert len(fake_mqtt.published) == before + 1
    _, payload = fake_mqtt.published[-1]
    assert payload["payload"]["addressee"] == "hoodFan"
    assert payload["payload"]["command"] == "set"
    assert payload["payload"]["value"] == "high"


async def test_set_hood_light_level_publishes_when_supported(
    aws_manager: tuple[AwsAppliancesManager, FakeMqttClient],
) -> None:
    manager, fake_mqtt = aws_manager
    mwo = manager.microwaves[0]
    ok = await mwo.set_hood_light_level(HoodLightLevel.Low)
    assert ok is True
    _, payload = fake_mqtt.published[-1]
    assert payload["payload"]["addressee"] == "hoodLight"
    assert payload["payload"]["value"] == "low"


async def test_set_hood_light_color_publishes_when_supported(
    aws_manager: tuple[AwsAppliancesManager, FakeMqttClient],
) -> None:
    manager, fake_mqtt = aws_manager
    mwo = manager.microwaves[0]
    ok = await mwo.set_hood_light_color(HoodLightColor.CoolWhite)
    assert ok is True
    _, payload = fake_mqtt.published[-1]
    assert payload["payload"]["addressee"] == "hoodLightColor"
    assert payload["payload"]["value"] == "coolWhite"


async def _manager_with_profile(
    auth: Auth,
    session: aiohttp.ClientSession,
    profile: dict[str, Any],
) -> tuple[AwsAppliancesManager, FakeMqttClient]:
    holder: dict[str, FakeMqttClient] = {}

    def _mqtt_factory(
        aws_auth: Any,
        message_callback: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> FakeMqttClient:
        fake = FakeMqttClient(aws_auth, message_callback)
        fake.set_getstate_reply(STATE)
        fake.set_capability_reply(MWO_CAP_PART, profile)
        holder["c"] = fake
        return fake

    class _Things:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def list_things(self) -> list[dict[str, Any]]:
            return [THING]

    with (
        patch(
            "whirlpool.awsiot.appliancesmanager.MqttClient",
            side_effect=_mqtt_factory,
        ),
        patch("whirlpool.awsiot.appliancesmanager.Things", _Things),
    ):
        manager = AwsAppliancesManager(auth, session, lambda: None)
        await manager.connect()
    return manager, holder["c"]


async def test_setters_return_false_when_capability_missing(
    auth: Auth,
    client_session_fixture: aiohttp.ClientSession,
) -> None:
    """Setters must not publish, must warn, must return False."""
    minimal_profile = {
        "capabilityPartNumber": MWO_CAP_PART,
        "features": ["microwaveOven"],
        "addressees": {"primaryCavity": ["set"]},  # no hood/mode addressees
    }
    manager, fake_mqtt = await _manager_with_profile(
        auth, client_session_fixture, minimal_profile
    )
    mwo = manager.microwaves[0]
    before = len(fake_mqtt.published)

    assert await mwo.set_hood_fan_speed(HoodFanSpeed.High) is False
    assert await mwo.set_hood_light_level(HoodLightLevel.Low) is False
    assert await mwo.set_hood_light_color(HoodLightColor.CoolWhite) is False
    assert await mwo.set_control_locked(True) is False
    assert await mwo.set_quiet_mode(True) is False
    assert await mwo.set_sabbath_mode(True) is False

    # Nothing got published.
    assert len(fake_mqtt.published) == before


async def test_mode_setters_publish_when_supported(
    auth: Auth,
    client_session_fixture: aiohttp.ClientSession,
) -> None:
    full_profile = {
        "capabilityPartNumber": MWO_CAP_PART,
        "features": ["microwaveOven"],
        "addressees": {
            "primaryCavity": ["set"],
            "hmiControlLockout": ["set"],
            "quietMode": ["set"],
            "sabbathMode": ["set"],
        },
    }
    manager, fake_mqtt = await _manager_with_profile(
        auth, client_session_fixture, full_profile
    )
    mwo = manager.microwaves[0]

    assert await mwo.set_control_locked(True) is True
    _, p1 = fake_mqtt.published[-1]
    assert p1["payload"]["addressee"] == "hmiControlLockout"
    assert p1["payload"]["value"] is True

    assert await mwo.set_quiet_mode(True) is True
    _, p2 = fake_mqtt.published[-1]
    assert p2["payload"]["addressee"] == "quietMode"

    assert await mwo.set_sabbath_mode(False) is True
    _, p3 = fake_mqtt.published[-1]
    assert p3["payload"]["addressee"] == "sabbathMode"
    assert p3["payload"]["value"] is False


_CAP_DIR = Path(__file__).parent / "data"


def _profile(name: str) -> CapabilityProfile:
    return parse_capability_profile(json.loads((_CAP_DIR / name).read_text()))


def _microwave(profile: CapabilityProfile) -> Microwave:
    appliance_info = ApplianceInfo(
        said="S1",
        name="MW",
        category="cooking",
        model_number="MODEL1",
        serial_number="SN1",
    )
    return Microwave(FakeMqttClient(), appliance_info, profile)


class TestMicrowaveSupports:
    def test_hood_model_supports_hood(self) -> None:
        mw = _microwave(_profile("capability_mwo.json"))
        assert mw.supports_hood_fan() is True
        assert mw.supports_hood_light_level() is True
        assert mw.supports_hood_light_color() is True
        assert mw.supports_quiet_mode() is True
        assert mw.supports_control_lock() is False
        assert mw.supports_sabbath_mode() is False

    def test_no_hood_model_lacks_hood(self) -> None:
        mw = _microwave(_profile("capability_mwo_no_hood.json"))
        assert mw.supports_hood_fan() is False
        assert mw.supports_hood_light_level() is False
        assert mw.supports_hood_light_color() is False
        assert mw.supports_quiet_mode() is True

    async def test_unsupported_setter_is_gated_and_sends_nothing(self) -> None:
        mw = _microwave(_profile("capability_mwo_no_hood.json"))
        mqtt = mw._mqttclient
        assert await mw.set_hood_light_level(HoodLightLevel.High) is False
        assert mqtt.published == []

    async def test_supported_setter_publishes(self) -> None:
        mw = _microwave(_profile("capability_mwo.json"))
        mqtt = mw._mqttclient
        assert await mw.set_hood_light_level(HoodLightLevel.High) is True
        assert any("hoodLight" in str(payload) for _topic, payload in mqtt.published)


async def test_capability_cached_across_same_model_things(
    auth: Auth,
    client_session_fixture: aiohttp.ClientSession,
) -> None:
    second_said = "WPR1A00000002"
    second_thing = {
        "thingName": second_said,
        "thingTypeName": MWO_MODEL,
        "attributes": {
            "Name": b"Second Microwave".hex(),
            "Category": "Cooking",
            "Serial": "D2",
            "CapabilityPartNumber": MWO_CAP_PART,
        },
    }

    fake_mqtt_holder: dict[str, FakeMqttClient] = {}

    def _mqtt_factory(
        aws_auth: Any,
        message_callback: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> FakeMqttClient:
        fake = FakeMqttClient(aws_auth, message_callback)
        fake.set_getstate_reply(STATE)
        fake.set_capability_reply(MWO_CAP_PART, MWO_CAPABILITY_PROFILE)
        fake_mqtt_holder["client"] = fake
        return fake

    class _Things:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        async def list_things(self) -> list[dict[str, Any]]:
            return [THING, second_thing]

    with (
        patch(
            "whirlpool.awsiot.appliancesmanager.MqttClient",
            side_effect=_mqtt_factory,
        ),
        patch("whirlpool.awsiot.appliancesmanager.Things", _Things),
    ):
        manager = AwsAppliancesManager(
            auth, client_session_fixture, lambda: None
        )
        await manager.connect()

    assert len(manager.microwaves) == 2
    cap_publishes = [
        (t, p)
        for t, p in fake_mqtt_holder["client"].published
        if t.startswith("api/capability/download/")
    ]
    assert len(cap_publishes) == 1
