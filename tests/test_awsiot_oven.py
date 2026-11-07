"""Tests for the AWS IoT oven implementation."""

import json
from collections.abc import AsyncGenerator, Awaitable, Callable
from pathlib import Path
from typing import Any

import aiohttp
import pytest
import pytest_asyncio
from aiointercept import aiointercept

from tests.awsiot.mocks import FakePahoBroker, mock_aws_api
from whirlpool.auth import Auth
from whirlpool.awsiot.appliancesmanager import AppliancesManager as AwsAppliancesManager
from whirlpool.awsiot.oven import Oven
from whirlpool.backendselector import BackendSelector
from whirlpool.oven import Cavity, CavityState, CookMode, CookOperation

_FIXTURE_DIR = Path(__file__).parent / "data" / "awsiot"

OVEN_THING: dict[str, Any] = json.loads(
    (_FIXTURE_DIR / "oven_thing.json").read_text(encoding="utf-8")
)
CAPABILITIES: dict[str, Any] = json.loads(
    (_FIXTURE_DIR / "capability_oven.json").read_text(encoding="utf-8")
)
STATE: dict[str, Any] = json.loads(
    (_FIXTURE_DIR / "oven_state.json").read_text(encoding="utf-8")
)

OVEN_SAID = OVEN_THING["thingName"]
OVEN_MODEL = OVEN_THING["thingTypeName"]
OVEN_CAP_PART = OVEN_THING["attributes"]["CapabilityPartNumber"]

type ConnectOven = Callable[..., Awaitable[tuple[Oven, FakePahoBroker]]]


@pytest_asyncio.fixture
async def connect_oven(
    auth: Auth,
    backend_selector: BackendSelector,
    client_session_fixture: aiohttp.ClientSession,
    aiointercept_mock: aiointercept,
    fake_paho_broker: FakePahoBroker,
) -> AsyncGenerator[ConnectOven]:
    """Connect an oven through the shared fake Paho broker."""
    managers: list[AwsAppliancesManager] = []

    async def _connect(
        capabilities: dict[str, Any] = CAPABILITIES,
        state: dict[str, Any] = STATE,
    ) -> tuple[Oven, FakePahoBroker]:
        part_number = capabilities["partNumber"]
        thing = {
            **OVEN_THING,
            "attributes": {
                **OVEN_THING["attributes"],
                "CapabilityPartNumber": part_number,
            },
        }
        mock_aws_api(
            aiointercept_mock,
            backend_selector,
            fake_paho_broker,
            [thing],
            {part_number: capabilities},
            state,
        )
        manager = AwsAppliancesManager(auth, client_session_fixture, lambda: None)
        assert await manager.connect() is True
        managers.append(manager)
        assert manager.microwaves == []
        assert len(manager.ovens) == 1
        oven = manager.ovens[0]
        return oven, fake_paho_broker

    yield _connect
    for manager in managers:
        await manager.disconnect()


def _body(broker: FakePahoBroker) -> dict[str, Any]:
    return broker.published[-1][1]["payload"]


async def test_two_cavities_and_state_getters(connect_oven: ConnectOven) -> None:
    oven, _ = await connect_oven()

    assert oven.get_oven_cavity_exists(Cavity.Upper)
    assert oven.get_oven_cavity_exists(Cavity.Lower)
    assert oven.get_cavity_state(Cavity.Upper) == CavityState.Standby
    assert oven.get_cavity_state(Cavity.Lower) == CavityState.Standby
    assert oven.get_door_opened(Cavity.Upper) is False
    assert oven.get_door_opened(Cavity.Lower) is False
    assert oven.get_light(Cavity.Upper) is False
    assert oven.get_light(Cavity.Lower) is False
    assert oven.get_temp(Cavity.Upper) is None
    assert oven.get_temp(Cavity.Lower) is None
    assert oven.get_target_temp(Cavity.Upper) is None
    assert oven.get_target_temp(Cavity.Lower) is None
    assert oven.get_cook_mode(Cavity.Upper) == CookMode.Standby
    assert oven.get_cook_mode(Cavity.Lower) == CookMode.Standby


async def test_light_command_uses_cavity_addressee(
    connect_oven: ConnectOven,
) -> None:
    oven, broker = await connect_oven()

    assert await oven.set_light(True, Cavity.Upper) is True
    assert _body(broker) == {
        "addressee": "primaryCavity",
        "command": "set",
        "cavityLight": True,
    }


@pytest.mark.parametrize(
    ("mode", "recipe", "target"),
    (
        (CookMode.Bake, "bake", 176.7),
        (CookMode.ConvectBake, "convectBake", 162.8),
        (CookMode.ConvectRoast, "convectRoast", 176.7),
        (CookMode.KeepWarm, "keepWarm", 76.7),
        (CookMode.AirFry, "airFry", 204.4),
    ),
)
async def test_validated_recipe_payloads(
    connect_oven: ConnectOven,
    mode: CookMode,
    recipe: str,
    target: float,
) -> None:
    oven, broker = await connect_oven()

    assert await oven.set_cook(target, mode, Cavity.Upper) is True
    assert _body(broker) == {
        "addressee": "primaryCavity",
        "command": "run",
        "recipeID": recipe,
        "targetTemperature": target,
    }


@pytest.mark.parametrize(
    ("mode", "requested", "expected"),
    (
        (CookMode.Broil, 287.78, 288),
        (CookMode.Broil, 232.22, 232.2),
        (CookMode.ConvectBroil, 232.22, 232),
    ),
)
async def test_discrete_temperature_recipes_snap_to_capability_values(
    connect_oven: ConnectOven,
    mode: CookMode,
    requested: float,
    expected: float,
) -> None:
    oven, broker = await connect_oven()

    assert await oven.set_cook(requested, mode, Cavity.Upper) is True
    body = _body(broker)
    assert body["targetTemperature"] == expected
    assert "broilLevelTemperature" not in body
    assert "cookTimer" not in body


async def test_set_cook_rejects_unsupported_optional_arguments(
    connect_oven: ConnectOven,
) -> None:
    oven, broker = await connect_oven()
    before = len(broker.published)

    with pytest.raises(ValueError, match="rapid_preheat"):
        await oven.set_cook(176.7, CookMode.Bake, rapid_preheat=True)
    with pytest.raises(ValueError, match="meat_probe_target_temp"):
        await oven.set_cook(176.7, CookMode.Bake, meat_probe_target_temp=70)
    with pytest.raises(ValueError, match="delay_cook"):
        await oven.set_cook(176.7, CookMode.Bake, delay_cook=3600)
    with pytest.raises(ValueError, match="operation_type"):
        await oven.set_cook(
            176.7,
            CookMode.Bake,
            operation_type=CookOperation.Cancel,
        )

    assert len(broker.published) == before


@pytest.mark.parametrize("target", [float("nan"), -100, 5000])
async def test_set_cook_rejects_invalid_broil_temperatures(
    connect_oven: ConnectOven,
    target: float,
) -> None:
    oven, broker = await connect_oven()
    before = len(broker.published)

    with pytest.raises(ValueError):
        await oven.set_cook(target, CookMode.Broil)

    assert len(broker.published) == before


async def test_cook_time_reads_cook_timer_time(connect_oven: ConnectOven) -> None:
    oven, _ = await connect_oven()

    assert oven.get_cook_time(Cavity.Upper) == 0
    assert oven.get_cook_time(Cavity.Lower) == 0


async def test_zero_temperatures_are_reported_as_none(
    connect_oven: ConnectOven,
) -> None:
    oven, _ = await connect_oven(
        state={
            **STATE,
            "primaryCavity": {
                **STATE["primaryCavity"],
                "ovenDisplayTemperature": 0,
                "targetTemperature": 0,
            },
        }
    )

    assert oven.get_temp(Cavity.Upper) is None
    assert oven.get_target_temp(Cavity.Upper) is None


async def test_non_oven_cavity_is_not_exposed_or_commanded(
    connect_oven: ConnectOven,
) -> None:
    capabilities = {
        "partNumber": OVEN_CAP_PART,
        "cavities": {
            "primaryCavity": {"cavityType": "oven"},
            "secondaryCavity": {"cavityType": "cooktop"},
        },
    }
    oven, broker = await connect_oven(capabilities)
    before = len(broker.published)

    assert oven.get_oven_cavity_exists(Cavity.Upper)
    assert not oven.get_oven_cavity_exists(Cavity.Lower)
    assert await oven.set_light(True, Cavity.Lower) is False
    assert await oven.set_cook(176.7, CookMode.Bake, Cavity.Lower) is False
    assert await oven.stop_cook(Cavity.Lower) is False
    assert len(broker.published) == before


async def test_unvalidated_capability_blocks_all_commands(
    connect_oven: ConnectOven,
) -> None:
    oven, broker = await connect_oven(_unvalidated_capabilities())
    before = len(broker.published)

    assert await oven.set_light(True, Cavity.Upper) is False
    assert await oven.set_cook(176.7, CookMode.Bake, Cavity.Upper) is False
    assert await oven.stop_cook(Cavity.Upper) is False
    assert len(broker.published) == before


async def test_remote_start_disabled_prevents_cook_command(
    connect_oven: ConnectOven,
) -> None:
    oven, broker = await connect_oven(state={**STATE, "remoteStartEnable": False})
    before = len(broker.published)

    assert await oven.set_cook(176.7, CookMode.Bake, Cavity.Upper) is False
    assert len(broker.published) == before


async def test_stop_uses_session_id_when_reported(connect_oven: ConnectOven) -> None:
    oven, broker = await connect_oven(
        state={
            **STATE,
            "secondaryCavity": {
                **STATE["secondaryCavity"],
                "sessionId": "lower-session",
            },
        }
    )

    assert await oven.stop_cook(Cavity.Lower) is True
    assert _body(broker) == {
        "addressee": "secondaryCavity",
        "command": "cancel",
        "sessionId": "lower-session",
    }


async def test_disconnected_presence_event_marks_oven_offline(
    connect_oven: ConnectOven,
) -> None:
    oven, _ = await connect_oven()

    oven.update_online(True)
    assert oven.get_online() is True
    oven.update_online(False)
    assert oven.get_online() is False


async def test_unsupported_controls_remain_explicitly_unsupported(
    connect_oven: ConnectOven,
) -> None:
    oven, _ = await connect_oven()

    assert oven.get_kitchen_timer().get_state() is None
    assert oven.get_sabbath_mode() is None


def _unvalidated_capabilities() -> dict[str, Any]:
    return {
        "partNumber": "W99999999",
        "cavities": {"primaryCavity": {"cavityType": "oven"}},
    }


async def test_unvalidated_capability_honors_disconnected_presence(
    connect_oven: ConnectOven,
) -> None:
    oven, _ = await connect_oven(_unvalidated_capabilities())

    oven.update_online(True)
    assert oven.get_online() is True
    oven.update_online(False)
    assert oven.get_online() is False


async def test_unvalidated_capability_does_not_claim_cook_control(
    connect_oven: ConnectOven,
) -> None:
    oven, broker = await connect_oven(_unvalidated_capabilities())
    before = len(broker.published)

    assert await oven.set_cook(176.7, CookMode.Bake, Cavity.Upper) is False
    assert len(broker.published) == before
