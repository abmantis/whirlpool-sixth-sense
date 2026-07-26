"""Integration tests for the AWS IoT Microwave class."""

import json
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import cast

import aiohttp
import pytest
import pytest_asyncio
from aiointercept import aiointercept

from tests.awsiot.mocks import (
    MWO_CAP_PART,
    MWO_CAPABILITY_PROFILE,
    MWO_MODEL,
    MWO_SAID,
    STATE,
    THING,
    FakeMqttClient,
    build_manager_with_profile,
    build_manager_with_things,
    make_mqtt_factory,
    mock_aws_http_api,
    patch_aws_manager_mqtt,
)
from whirlpool.auth import Auth
from whirlpool.awsiot.appliancesmanager import AppliancesManager as AwsAppliancesManager
from whirlpool.awsiot.capabilities import (
    MicrowaveCapabilityProfile,
    parse_microwave_capability_profile,
)
from whirlpool.awsiot.microwave import Microwave
from whirlpool.awsiot.mqttclient import MqttClient
from whirlpool.backendselector import BackendSelector
from whirlpool.microwave import (
    HoodFanSpeed,
    HoodLightColor,
    HoodLightLevel,
    MicrowaveCavityState,
    MicrowaveDoorStatus,
)
from whirlpool.types import ApplianceInfo

_CAP_DIR = Path(__file__).parent / "data" / "awsiot"


@pytest_asyncio.fixture
async def aws_manager(
    auth: Auth,
    backend_selector: BackendSelector,
    client_session_fixture: aiohttp.ClientSession,
    aiointercept_mock: aiointercept,
) -> AsyncGenerator[tuple[AwsAppliancesManager, FakeMqttClient]]:
    """An AwsAppliancesManager connected to a fake MQTT + wire-mocked HTTP."""

    fake_mqtt_holder: dict[str, FakeMqttClient] = {}
    mqtt_factory = make_mqtt_factory(
        STATE, {MWO_CAP_PART: MWO_CAPABILITY_PROFILE}, fake_mqtt_holder
    )
    mock_aws_http_api(aiointercept_mock, backend_selector, [THING])

    with patch_aws_manager_mqtt(mqtt_factory):
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
    backend_selector: BackendSelector,
    client_session_fixture: aiohttp.ClientSession,
    aiointercept_mock: aiointercept,
) -> None:
    """An appliance whose state only has a few fields shouldn't crash getters."""

    mqtt_factory = make_mqtt_factory(
        {"primaryCavity": {"cavityState": "idle"}},
        {MWO_CAP_PART: MWO_CAPABILITY_PROFILE},
    )
    mock_aws_http_api(aiointercept_mock, backend_selector, [THING])

    with patch_aws_manager_mqtt(mqtt_factory):
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
    fake_mqtt.inject(f"dt/{MWO_MODEL}/{MWO_SAID}/state/update", new_state)

    assert mwo.get_cavity_state() == MicrowaveCavityState.Cooking
    assert mwo.get_cavity_light() is True


async def test_attr_callback_fires_on_state_update(
    aws_manager: tuple[AwsAppliancesManager, FakeMqttClient],
) -> None:
    manager, fake_mqtt = aws_manager
    mwo = manager.microwaves[0]
    calls: list[int] = []
    mwo.register_attr_callback(lambda: calls.append(1))

    fake_mqtt.inject(f"dt/{MWO_MODEL}/{MWO_SAID}/state/update", STATE)
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
    assert topic == (f"cmd/{MWO_MODEL}/{MWO_SAID}/request/{fake_mqtt.client_id}")
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
    assert mwo.capability_profile.supports_hood_fan
    assert mwo.capability_profile.supports_quiet_mode


async def test_cooking_without_microwave_feature_routes_to_oven(
    auth: Auth,
    backend_selector: BackendSelector,
    client_session_fixture: aiohttp.ClientSession,
    aiointercept_mock: aiointercept,
) -> None:
    oven_part = "W99999999"
    oven_profile = {
        "partNumber": oven_part,
        "cavities": {"primaryCavity": {"cavityType": "oven"}},
    }
    oven_thing = {
        **THING,
        "attributes": {**THING["attributes"], "CapabilityPartNumber": oven_part},
    }

    manager = await build_manager_with_things(
        auth,
        client_session_fixture,
        aiointercept_mock,
        backend_selector,
        [oven_thing],
        {oven_part: oven_profile},
    )
    assert manager.microwaves == []
    assert len(manager.ovens) == 1


async def test_missing_capability_part_number_skips_appliance(
    auth: Auth,
    backend_selector: BackendSelector,
    client_session_fixture: aiohttp.ClientSession,
    aiointercept_mock: aiointercept,
) -> None:
    attrs = {
        k: v for k, v in THING["attributes"].items() if k != "CapabilityPartNumber"
    }
    bad_thing = {**THING, "attributes": attrs}

    manager = await build_manager_with_things(
        auth,
        client_session_fixture,
        aiointercept_mock,
        backend_selector,
        [bad_thing],
        {},
    )
    assert manager.all_appliances == {}


async def test_capability_download_failure_skips_appliance(
    auth: Auth,
    backend_selector: BackendSelector,
    client_session_fixture: aiohttp.ClientSession,
    aiointercept_mock: aiointercept,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Shrink the real 10s-per-attempt timeout so the retry path runs fast.
    from whirlpool.awsiot import capabilities as cap_mod

    monkeypatch.setattr(cap_mod, "CAPABILITY_DOWNLOAD_TIMEOUT", 0.01)
    monkeypatch.setattr(cap_mod, "CAPABILITY_DOWNLOAD_RETRIES", 2)

    manager = await build_manager_with_things(
        auth,
        client_session_fixture,
        aiointercept_mock,
        backend_selector,
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


async def test_setters_return_false_when_capability_missing(
    auth: Auth,
    backend_selector: BackendSelector,
    client_session_fixture: aiohttp.ClientSession,
    aiointercept_mock: aiointercept,
) -> None:
    """Setters must not publish, must warn, must return False."""
    # Real-schema microwave that advertises no hood sections, no capability
    # flags, and no sabbath recipes -> every supports_* is False.
    minimal_profile = {
        "partNumber": MWO_CAP_PART,
        "cavities": {"primaryCavity": {"cavityType": "microwaveOven"}},
    }
    manager, fake_mqtt = await build_manager_with_profile(
        auth,
        client_session_fixture,
        aiointercept_mock,
        backend_selector,
        minimal_profile,
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
    backend_selector: BackendSelector,
    client_session_fixture: aiohttp.ClientSession,
    aiointercept_mock: aiointercept,
) -> None:
    full_profile = {
        "partNumber": MWO_CAP_PART,
        "cavities": {
            "primaryCavity": {
                "cavityType": "microwaveOven",
                # A non-empty sabbathRecipes dict is what marks sabbath as supported.
                "sabbathRecipes": {"sabbath": {}},
            }
        },
        "supportsHmiControlLockout": True,
        "quietMode": True,
    }
    manager, fake_mqtt = await build_manager_with_profile(
        auth, client_session_fixture, aiointercept_mock, backend_selector, full_profile
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


def _profile(name: str) -> MicrowaveCapabilityProfile:
    return parse_microwave_capability_profile(json.loads((_CAP_DIR / name).read_text()))


def _microwave(
    profile: MicrowaveCapabilityProfile,
) -> tuple[Microwave, FakeMqttClient]:
    appliance_info = ApplianceInfo(
        said="S1",
        name="MW",
        category="cooking",
        model_number="MODEL1",
        serial_number="SN1",
    )
    mqtt = FakeMqttClient()
    return Microwave(cast(MqttClient, mqtt), appliance_info, profile), mqtt


class TestMicrowaveSupports:
    def test_hood_model_supports_hood(self) -> None:
        mw, _ = _microwave(_profile("capability_mwo.json"))
        assert mw.supports_hood_fan() is True
        assert mw.supports_hood_light_level() is True
        assert mw.supports_hood_light_color() is True
        assert mw.supports_quiet_mode() is True
        assert mw.supports_control_lock() is False
        assert mw.supports_sabbath_mode() is False

    def test_no_hood_model_lacks_hood(self) -> None:
        mw, _ = _microwave(_profile("capability_mwo_no_hood.json"))
        assert mw.supports_hood_fan() is False
        assert mw.supports_hood_light_level() is False
        assert mw.supports_hood_light_color() is False
        assert mw.supports_quiet_mode() is True
        assert mw.supports_control_lock() is False
        assert mw.supports_sabbath_mode() is False

    async def test_unsupported_setter_is_gated_and_sends_nothing(self) -> None:
        mw, mqtt = _microwave(_profile("capability_mwo_no_hood.json"))
        assert await mw.set_hood_light_level(HoodLightLevel.High) is False
        assert mqtt.published == []

    async def test_supported_setter_publishes(self) -> None:
        mw, mqtt = _microwave(_profile("capability_mwo.json"))
        assert await mw.set_hood_light_level(HoodLightLevel.High) is True
        assert any("hoodLight" in str(payload) for _topic, payload in mqtt.published)


async def test_capability_cached_across_same_model_things(
    auth: Auth,
    backend_selector: BackendSelector,
    client_session_fixture: aiohttp.ClientSession,
    aiointercept_mock: aiointercept,
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
    mqtt_factory = make_mqtt_factory(
        STATE, {MWO_CAP_PART: MWO_CAPABILITY_PROFILE}, fake_mqtt_holder
    )
    mock_aws_http_api(aiointercept_mock, backend_selector, [THING, second_thing])

    with patch_aws_manager_mqtt(mqtt_factory):
        manager = AwsAppliancesManager(auth, client_session_fixture, lambda: None)
        await manager.connect()

    assert len(manager.microwaves) == 2
    cap_publishes = [
        (t, p)
        for t, p in fake_mqtt_holder["client"].published
        if t.startswith("api/capability/download/")
    ]
    assert len(cap_publishes) == 1
