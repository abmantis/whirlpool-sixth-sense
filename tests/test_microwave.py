"""Integration tests for the AWS IoT Microwave class."""

import json
from collections.abc import AsyncGenerator, Awaitable, Callable
from pathlib import Path
from typing import Any

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
    FakePahoBroker,
    mock_aws_api,
)
from whirlpool.auth import Auth
from whirlpool.awsiot.appliancesmanager import AppliancesManager as AwsAppliancesManager
from whirlpool.awsiot.microwave import Microwave
from whirlpool.backendselector import BackendSelector
from whirlpool.microwave import (
    HoodFanSpeed,
    HoodLightColor,
    HoodLightLevel,
    MicrowaveCavityState,
    MicrowaveDoorStatus,
    Recipe,
)

_CAP_DIR = Path(__file__).parent / "data" / "awsiot"

type ConnectAwsManager = Callable[..., Awaitable[AwsAppliancesManager]]


@pytest_asyncio.fixture
async def aws_manager(
    auth: Auth,
    client_session_fixture: aiohttp.ClientSession,
    aws_api_mock: FakePahoBroker,
) -> AsyncGenerator[tuple[AwsAppliancesManager, FakePahoBroker]]:
    """An AwsAppliancesManager connected to the fake broker + wire-mocked HTTP."""
    manager = AwsAppliancesManager(auth, client_session_fixture, lambda: None)
    ok = await manager.connect()
    assert ok is True
    yield manager, aws_api_mock
    await manager.disconnect()


@pytest_asyncio.fixture
async def connect_aws_manager(
    auth: Auth,
    backend_selector: BackendSelector,
    client_session_fixture: aiohttp.ClientSession,
    aiointercept_mock: aiointercept,
    fake_paho_broker: FakePahoBroker,
) -> AsyncGenerator[ConnectAwsManager]:
    """Connect an AwsAppliancesManager over the given things, with the broker
    answering capability downloads and getState as `mock_aws_api` sets up."""
    managers: list[AwsAppliancesManager] = []

    async def _connect(
        things: list[dict[str, Any]],
        capabilities: dict[str, dict[str, Any] | None],
        state: dict[str, Any] = STATE,
    ) -> AwsAppliancesManager:
        mock_aws_api(
            aiointercept_mock,
            backend_selector,
            fake_paho_broker,
            things,
            capabilities,
            state,
        )
        manager = AwsAppliancesManager(auth, client_session_fixture, lambda: None)
        assert await manager.connect() is True
        managers.append(manager)
        return manager

    yield _connect
    for manager in managers:
        await manager.disconnect()


async def test_cooking_category_registers_microwave(
    aws_manager: tuple[AwsAppliancesManager, FakePahoBroker],
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
    aws_manager: tuple[AwsAppliancesManager, FakePahoBroker],
) -> None:
    _, broker = aws_manager
    cid = broker.client_id
    assert {
        f"cmd/{MWO_MODEL}/{MWO_SAID}/response/{cid}",
        f"dt/{MWO_MODEL}/{MWO_SAID}/state/update",
        f"$aws/events/presence/connected/{MWO_SAID}",
        f"$aws/events/presence/disconnected/{MWO_SAID}",
    }.issubset(broker.subscribed_topics)


async def test_initial_state_populates_getters(
    aws_manager: tuple[AwsAppliancesManager, FakePahoBroker],
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
    connect_aws_manager: ConnectAwsManager,
) -> None:
    """An appliance whose state only has a few fields shouldn't crash getters."""

    manager = await connect_aws_manager(
        [THING],
        {MWO_CAP_PART: MWO_CAPABILITY_PROFILE},
        state={"primaryCavity": {"cavityState": "idle"}},
    )

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
    aws_manager: tuple[AwsAppliancesManager, FakePahoBroker],
) -> None:
    manager, broker = aws_manager
    mwo = manager.microwaves[0]

    new_state = {**STATE}
    new_state["primaryCavity"] = {
        **STATE["primaryCavity"],
        "cavityState": "cooking",
        "cavityLight": True,
    }
    await broker.inject(f"dt/{MWO_MODEL}/{MWO_SAID}/state/update", new_state)

    assert mwo.get_cavity_state() == MicrowaveCavityState.Cooking
    assert mwo.get_cavity_light() is True


async def test_attr_callback_fires_on_state_update(
    aws_manager: tuple[AwsAppliancesManager, FakePahoBroker],
) -> None:
    manager, broker = aws_manager
    mwo = manager.microwaves[0]
    calls: list[int] = []
    mwo.register_attr_callback(lambda: calls.append(1))

    await broker.inject(f"dt/{MWO_MODEL}/{MWO_SAID}/state/update", STATE)
    assert calls == [1]


async def test_set_cavity_light_publishes_expected_command(
    aws_manager: tuple[AwsAppliancesManager, FakePahoBroker],
) -> None:
    manager, broker = aws_manager
    mwo = manager.microwaves[0]

    before = len(broker.published)
    ok = await mwo.set_cavity_light(True)
    assert ok is True

    assert len(broker.published) == before + 1
    topic, payload = broker.published[-1]
    assert topic == (f"cmd/{MWO_MODEL}/{MWO_SAID}/request/{broker.client_id}")
    assert payload["payload"]["addressee"] == "primaryCavity"
    assert payload["payload"]["command"] == "set"
    assert payload["payload"]["cavityLight"] is True


async def test_unknown_cavity_state_maps_to_none(
    aws_manager: tuple[AwsAppliancesManager, FakePahoBroker],
) -> None:
    manager, broker = aws_manager
    mwo = manager.microwaves[0]

    await broker.inject(
        f"dt/{MWO_MODEL}/{MWO_SAID}/state/update",
        {**STATE, "primaryCavity": {**STATE["primaryCavity"], "cavityState": "bogus"}},
    )
    assert mwo.get_cavity_state() is None


async def test_cook_timer_time_complete_returns_timestamp(
    aws_manager: tuple[AwsAppliancesManager, FakePahoBroker],
) -> None:
    manager, broker = aws_manager
    mwo = manager.microwaves[0]

    await broker.inject(
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


# A partial state, the way a push carries it.
_DOOR_OPEN = {"primaryCavity": {"doorStatus": "open"}}


async def _inject_presence(
    broker: FakePahoBroker, event: str, said: str = MWO_SAID
) -> None:
    await broker.inject(
        f"$aws/events/presence/{event}/{said}",
        {"eventType": event, "clientId": "device", "timestamp": 1},
        # Nothing subscribes to an unknown appliance's topics.
        unsolicited=said != MWO_SAID,
    )


async def _inject_state(
    broker: FakePahoBroker, kind: str, said: str = MWO_SAID
) -> None:
    """Inject a getState reply (`kind` "reply") or a state push ("push")."""
    if kind == "reply":
        topic = f"cmd/{MWO_MODEL}/{said}/response/{broker.client_id}"
        payload = {"requestId": "1", "response": "accepted", "payload": _DOOR_OPEN}
    else:
        topic = f"dt/{MWO_MODEL}/{said}/state/update"
        payload = _DOOR_OPEN
    # Nothing subscribes to an unknown appliance's topics.
    await broker.inject(topic, payload, unsolicited=said != MWO_SAID)


async def test_get_online_is_true_once_getstate_is_answered(
    aws_manager: tuple[AwsAppliancesManager, FakePahoBroker],
) -> None:
    # connect() sent getState and the fake answered it. No presence event came
    # in, as for an appliance that was already connected.
    manager, _ = aws_manager
    mwo = manager.microwaves[0]
    assert mwo.get_online() is True


@pytest.mark.parametrize("kind", ["reply", "push"])
async def test_state_message_marks_online_after_a_disconnect(
    aws_manager: tuple[AwsAppliancesManager, FakePahoBroker], kind: str
) -> None:
    manager, broker = aws_manager
    mwo = manager.microwaves[0]
    await _inject_presence(broker, "disconnected")
    assert mwo.get_online() is False
    calls: list[bool | None] = []
    mwo.register_attr_callback(lambda: calls.append(mwo.get_online()))

    await _inject_state(broker, kind)

    assert mwo.get_online() is True
    assert mwo.get_door_status() == MicrowaveDoorStatus.Open
    # The state callback runs first and still reads offline. The online change
    # runs second, so the callback that makes the appliance available already
    # sees the new state.
    assert calls == [False, True]


async def test_online_follows_disconnects_and_pushes(
    aws_manager: tuple[AwsAppliancesManager, FakePahoBroker],
) -> None:
    manager, broker = aws_manager
    mwo = manager.microwaves[0]
    calls: list[bool | None] = []
    mwo.register_attr_callback(lambda: calls.append(mwo.get_online()))

    await _inject_presence(broker, "disconnected")
    assert mwo.get_online() is False
    await _inject_state(broker, "push")
    assert mwo.get_online() is True
    await _inject_state(broker, "push")
    await _inject_presence(broker, "disconnected")
    assert mwo.get_online() is False
    await _inject_state(broker, "push")
    assert mwo.get_online() is True

    # Each push calls back once for its state and once more only if it brings
    # the appliance back online: the second push, already online, adds none.
    assert calls == [False, False, True, True, False, False, True]


@pytest.mark.parametrize(
    "reply",
    (
        pytest.param({"requestId": "1", "response": "accepted"}, id="ack"),
        pytest.param(
            {
                "requestId": "2",
                "response": "rejected",
                "payload": {"errorCode": "C000"},
            },
            id="rejected",
        ),
    ),
)
async def test_reply_without_state_does_not_mark_online(
    aws_manager: tuple[AwsAppliancesManager, FakePahoBroker], reply: dict[str, Any]
) -> None:
    # Which side sends a command ack or a rejection, the appliance or the
    # cloud, has not been observed. Only a reply that carries state counts.
    manager, broker = aws_manager
    mwo = manager.microwaves[0]
    await _inject_presence(broker, "disconnected")

    await broker.inject(
        f"cmd/{MWO_MODEL}/{MWO_SAID}/response/{broker.client_id}", reply
    )

    assert mwo.get_online() is False


@pytest.mark.parametrize("kind", ["reply", "push"])
async def test_state_message_for_unknown_said_leaves_online_alone(
    aws_manager: tuple[AwsAppliancesManager, FakePahoBroker],
    kind: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    manager, broker = aws_manager
    mwo = manager.microwaves[0]
    await _inject_presence(broker, "disconnected")
    calls: list[bool | None] = []
    mwo.register_attr_callback(lambda: calls.append(mwo.get_online()))

    await _inject_state(broker, kind, said="UNKNOWN_SAID")

    assert mwo.get_online() is False
    assert calls == []
    assert "unknown appliance UNKNOWN_SAID" in caplog.text


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
    aws_manager: tuple[AwsAppliancesManager, FakePahoBroker],
    events: tuple[str, ...],
    expected_online: bool,
    expected_callback_states: list[bool],
) -> None:
    manager, broker = aws_manager
    mwo = manager.microwaves[0]
    # The answered getState left it online; start each case from offline.
    await _inject_presence(broker, "disconnected")
    calls: list[bool | None] = []
    mwo.register_attr_callback(lambda: calls.append(mwo.get_online()))

    for timestamp, event in enumerate(events, start=1):
        await broker.inject(
            f"$aws/events/presence/{event}/{MWO_SAID}",
            {"eventType": event, "clientId": "device", "timestamp": timestamp},
        )

    assert mwo.get_online() is expected_online
    assert calls == expected_callback_states


async def test_presence_for_unknown_said_is_ignored(
    aws_manager: tuple[AwsAppliancesManager, FakePahoBroker],
) -> None:
    manager, broker = aws_manager
    mwo = manager.microwaves[0]

    await _inject_presence(broker, "disconnected", said="UNKNOWN_SAID")
    assert mwo.get_online() is True


async def test_capability_profile_exposed_on_appliance(
    aws_manager: tuple[AwsAppliancesManager, FakePahoBroker],
) -> None:
    """The profile should be attached so callers can gate further setters."""
    manager, _ = aws_manager
    mwo = manager.microwaves[0]
    assert mwo.capability_profile.part_number == MWO_CAP_PART
    assert mwo.capability_profile.supports_hood_fan
    assert mwo.capability_profile.supports_quiet_mode


async def test_cooking_without_microwave_feature_skips_appliance(
    connect_aws_manager: ConnectAwsManager,
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

    manager = await connect_aws_manager([oven_thing], {oven_part: oven_profile})
    assert manager.microwaves == []
    assert manager.all_appliances == {}


async def test_missing_capability_part_number_skips_appliance(
    connect_aws_manager: ConnectAwsManager,
) -> None:
    attrs = {
        k: v for k, v in THING["attributes"].items() if k != "CapabilityPartNumber"
    }
    bad_thing = {**THING, "attributes": attrs}

    manager = await connect_aws_manager([bad_thing], {})
    assert manager.all_appliances == {}


async def test_capability_download_failure_skips_appliance(
    connect_aws_manager: ConnectAwsManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Shrink the real 10s-per-attempt timeout so the retry path runs fast.
    from whirlpool.awsiot import capabilities as cap_mod

    monkeypatch.setattr(cap_mod, "CAPABILITY_DOWNLOAD_TIMEOUT", 0.01)
    monkeypatch.setattr(cap_mod, "CAPABILITY_DOWNLOAD_RETRIES", 2)

    # no reply → timeout → skip
    manager = await connect_aws_manager([THING], {MWO_CAP_PART: None})
    assert manager.all_appliances == {}


async def test_set_hood_fan_speed_publishes_when_supported(
    aws_manager: tuple[AwsAppliancesManager, FakePahoBroker],
) -> None:
    manager, broker = aws_manager
    mwo = manager.microwaves[0]
    before = len(broker.published)
    ok = await mwo.set_hood_fan_speed(HoodFanSpeed.High)
    assert ok is True
    assert len(broker.published) == before + 1
    _, payload = broker.published[-1]
    assert payload["payload"]["addressee"] == "hoodFan"
    assert payload["payload"]["command"] == "set"
    assert payload["payload"]["value"] == "high"


async def test_set_hood_light_level_publishes_when_supported(
    aws_manager: tuple[AwsAppliancesManager, FakePahoBroker],
) -> None:
    manager, broker = aws_manager
    mwo = manager.microwaves[0]
    ok = await mwo.set_hood_light_level(HoodLightLevel.Low)
    assert ok is True
    _, payload = broker.published[-1]
    assert payload["payload"]["addressee"] == "hoodLight"
    assert payload["payload"]["value"] == "low"


async def test_set_hood_light_color_publishes_when_supported(
    aws_manager: tuple[AwsAppliancesManager, FakePahoBroker],
) -> None:
    manager, broker = aws_manager
    mwo = manager.microwaves[0]
    ok = await mwo.set_hood_light_color(HoodLightColor.CoolWhite)
    assert ok is True
    _, payload = broker.published[-1]
    assert payload["payload"]["addressee"] == "hoodLightColor"
    assert payload["payload"]["value"] == "coolWhite"


async def test_setters_return_false_when_capability_missing(
    connect_aws_manager: ConnectAwsManager,
    fake_paho_broker: FakePahoBroker,
) -> None:
    """Setters must not publish, must warn, must return False."""
    # Real-schema microwave that advertises no hood sections, no capability
    # flags, and no sabbath recipes -> every supports_* is False.
    minimal_profile = {
        "partNumber": MWO_CAP_PART,
        "cavities": {"primaryCavity": {"cavityType": "microwaveOven"}},
    }
    manager = await connect_aws_manager([THING], {MWO_CAP_PART: minimal_profile})
    mwo = manager.microwaves[0]
    before = len(fake_paho_broker.published)

    assert await mwo.set_hood_fan_speed(HoodFanSpeed.High) is False
    assert await mwo.set_hood_light_level(HoodLightLevel.Low) is False
    assert await mwo.set_hood_light_color(HoodLightColor.CoolWhite) is False
    assert await mwo.set_control_locked(True) is False
    assert await mwo.set_quiet_mode(True) is False
    assert await mwo.set_sabbath_mode(True) is False

    # Nothing got published.
    assert len(fake_paho_broker.published) == before


async def test_mode_setters_publish_when_supported(
    connect_aws_manager: ConnectAwsManager,
    fake_paho_broker: FakePahoBroker,
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
    manager = await connect_aws_manager([THING], {MWO_CAP_PART: full_profile})
    mwo = manager.microwaves[0]

    assert await mwo.set_control_locked(True) is True
    _, p1 = fake_paho_broker.published[-1]
    assert p1["payload"]["addressee"] == "hmiControlLockout"
    assert p1["payload"]["value"] is True

    assert await mwo.set_quiet_mode(True) is True
    _, p2 = fake_paho_broker.published[-1]
    assert p2["payload"]["addressee"] == "quietMode"

    assert await mwo.set_sabbath_mode(False) is True
    _, p3 = fake_paho_broker.published[-1]
    assert p3["payload"]["addressee"] == "sabbathMode"
    assert p3["payload"]["value"] is False


async def _microwave(
    connect_aws_manager: ConnectAwsManager, profile_file: str
) -> Microwave:
    profile = json.loads((_CAP_DIR / profile_file).read_text())
    manager = await connect_aws_manager([THING], {MWO_CAP_PART: profile})
    return manager.microwaves[0]


class TestMicrowaveSupports:
    async def test_hood_model_supports_hood(
        self, connect_aws_manager: ConnectAwsManager
    ) -> None:
        mw = await _microwave(connect_aws_manager, "capability_mwo.json")
        assert mw.supports_hood_fan() is True
        assert mw.supports_hood_light_level() is True
        assert mw.supports_hood_light_color() is True
        assert mw.supports_quiet_mode() is True
        assert mw.supports_control_lock() is False
        assert mw.supports_sabbath_mode() is False

    async def test_no_hood_model_lacks_hood(
        self, connect_aws_manager: ConnectAwsManager
    ) -> None:
        mw = await _microwave(connect_aws_manager, "capability_mwo_no_hood.json")
        assert mw.supports_hood_fan() is False
        assert mw.supports_hood_light_level() is False
        assert mw.supports_hood_light_color() is False
        assert mw.supports_quiet_mode() is True
        assert mw.supports_control_lock() is False
        assert mw.supports_sabbath_mode() is False

    async def test_unsupported_setter_is_gated_and_sends_nothing(
        self,
        connect_aws_manager: ConnectAwsManager,
        fake_paho_broker: FakePahoBroker,
    ) -> None:
        mw = await _microwave(connect_aws_manager, "capability_mwo_no_hood.json")
        before = len(fake_paho_broker.published)
        assert await mw.set_hood_light_level(HoodLightLevel.High) is False
        assert len(fake_paho_broker.published) == before

    async def test_supported_setter_publishes(
        self,
        connect_aws_manager: ConnectAwsManager,
        fake_paho_broker: FakePahoBroker,
    ) -> None:
        mw = await _microwave(connect_aws_manager, "capability_mwo.json")
        assert await mw.set_hood_light_level(HoodLightLevel.High) is True
        assert any(
            "hoodLight" in str(payload)
            for _topic, payload in fake_paho_broker.published
        )


async def test_capability_cached_across_same_model_things(
    connect_aws_manager: ConnectAwsManager,
    fake_paho_broker: FakePahoBroker,
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

    manager = await connect_aws_manager(
        [THING, second_thing], {MWO_CAP_PART: MWO_CAPABILITY_PROFILE}
    )

    assert len(manager.microwaves) == 2
    cap_publishes = [
        (t, p)
        for t, p in fake_paho_broker.published
        if t.startswith("api/capability/download/")
    ]
    assert len(cap_publishes) == 1


async def test_start_cook_publishes_expected_payload(
    aws_manager: tuple[AwsAppliancesManager, FakePahoBroker],
) -> None:
    manager, broker = aws_manager
    mwo = manager.microwaves[0]

    before = len(broker.published)
    ok = await mwo.set_cook(Recipe.Microwave, 30, power_level=50)
    assert ok is True

    assert len(broker.published) == before + 1
    topic, payload = broker.published[-1]
    assert topic == f"cmd/{MWO_MODEL}/{MWO_SAID}/request/{broker.client_id}"
    body = payload["payload"]
    assert body["addressee"] == "primaryCavity"
    assert body["command"] == "run"
    assert body["recipeID"] == "microwave"
    assert body["mwoPowerLevel"] == 50.0
    assert isinstance(body["mwoPowerLevel"], float)
    assert body["cookTimer"] == {"command": "run", "time": 30}


async def test_start_cook_returns_false_when_remote_start_disabled(
    aws_manager: tuple[AwsAppliancesManager, FakePahoBroker],
) -> None:
    manager, broker = aws_manager
    mwo = manager.microwaves[0]

    # Disable remote start via state update.
    await broker.inject(
        f"dt/{MWO_MODEL}/{MWO_SAID}/state/update",
        {**STATE, "remoteStartEnable": False},
    )

    before = len(broker.published)
    ok = await mwo.set_cook(Recipe.Reheat, 60)
    assert ok is False
    assert len(broker.published) == before  # nothing published


# capability_mwo.json: microwave.mwoPowerLevel range is 10..100 step 10
@pytest.mark.parametrize("power_level", [0, -1, 5, 55, 101, 200])
async def test_start_cook_rejects_power_level_outside_capability_range(
    aws_manager: tuple[AwsAppliancesManager, FakePahoBroker],
    power_level: int,
) -> None:
    manager, broker = aws_manager
    mwo = manager.microwaves[0]
    before = len(broker.published)
    with pytest.raises(ValueError):
        await mwo.set_cook(Recipe.Microwave, 30, power_level=power_level)
    assert len(broker.published) == before


async def test_start_cook_requires_power_level_for_editable_recipe(
    aws_manager: tuple[AwsAppliancesManager, FakePahoBroker],
) -> None:
    manager, broker = aws_manager
    mwo = manager.microwaves[0]
    before = len(broker.published)
    with pytest.raises(ValueError):
        await mwo.set_cook(Recipe.Microwave, 30)
    assert len(broker.published) == before


# capability_mwo.json: cookTime range is 5..5940 step 1
@pytest.mark.parametrize("duration", [0, -5, 4, 5941])
async def test_start_cook_rejects_duration_outside_capability_range(
    aws_manager: tuple[AwsAppliancesManager, FakePahoBroker],
    duration: int,
) -> None:
    manager, broker = aws_manager
    mwo = manager.microwaves[0]
    before = len(broker.published)
    with pytest.raises(ValueError):
        await mwo.set_cook(Recipe.Microwave, duration, power_level=50)
    assert len(broker.published) == before


@pytest.mark.parametrize(
    "recipe,fixed_power",
    [(Recipe.Reheat, 70), (Recipe.Defrost, 20), (Recipe.Soften, 20)],
)
async def test_start_cook_fixed_power_recipes_omit_power_level(
    aws_manager: tuple[AwsAppliancesManager, FakePahoBroker],
    recipe: Recipe,
    fixed_power: int,
) -> None:
    """Recipes with mwoPowerLevel under nonEditableOptions must not send it."""
    manager, broker = aws_manager
    mwo = manager.microwaves[0]

    options = mwo.get_recipe_options(recipe)
    assert options is not None
    assert options.power_level is None
    assert options.fixed_power_level == fixed_power

    ok = await mwo.set_cook(recipe, 60)
    assert ok is True
    body = broker.published[-1][1]["payload"]
    assert body["recipeID"] == recipe.value
    assert "mwoPowerLevel" not in body
    assert body["cookTimer"] == {"command": "run", "time": 60}


async def test_start_cook_rejects_power_level_for_fixed_power_recipe(
    aws_manager: tuple[AwsAppliancesManager, FakePahoBroker],
) -> None:
    manager, broker = aws_manager
    mwo = manager.microwaves[0]
    before = len(broker.published)
    with pytest.raises(ValueError, match="fixed power level of 70"):
        await mwo.set_cook(Recipe.Reheat, 60, power_level=100)
    assert len(broker.published) == before


async def test_command_acks_and_rejections_do_not_touch_state(
    aws_manager: tuple[AwsAppliancesManager, FakePahoBroker],
) -> None:
    manager, broker = aws_manager
    mwo = manager.microwaves[0]
    before = mwo.get_raw_data()
    topic = f"cmd/{MWO_MODEL}/{MWO_SAID}/response/{broker.client_id}"

    await broker.inject(topic, {"requestId": "1", "response": "accepted"})
    await broker.inject(
        topic,
        {"requestId": "2", "response": "rejected", "payload": {"errorCode": "C000"}},
    )

    assert mwo.get_raw_data() == before


async def test_cancel_cook_publishes_expected_payload(
    aws_manager: tuple[AwsAppliancesManager, FakePahoBroker],
) -> None:
    manager, broker = aws_manager
    mwo = manager.microwaves[0]

    before = len(broker.published)
    ok = await mwo.stop_cook()
    assert ok is True

    assert len(broker.published) == before + 1
    _, payload = broker.published[-1]
    body = payload["payload"]
    assert body["addressee"] == "primaryCavity"
    assert body["command"] == "cancel"


@pytest.mark.parametrize(
    "recipe,wire_value",
    [
        (Recipe.Microwave, "microwave"),
        (Recipe.Reheat, "reheat"),
        (Recipe.Defrost, "defrost"),
        (Recipe.Soften, "soften"),
    ],
)
async def test_start_cook_recipe_enum_wire_value(
    aws_manager: tuple[AwsAppliancesManager, FakePahoBroker],
    recipe: Recipe,
    wire_value: str,
) -> None:
    manager, broker = aws_manager
    mwo = manager.microwaves[0]
    if recipe is Recipe.Microwave:
        await mwo.set_cook(recipe, 30, power_level=50)
    else:
        await mwo.set_cook(recipe, 30)
    _, payload = broker.published[-1]
    assert payload["payload"]["recipeID"] == wire_value
