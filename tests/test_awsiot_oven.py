"""Tests for the AWS IoT oven implementation."""

from typing import cast

import pytest

from tests.awsiot.mocks import FakeMqttClient
from whirlpool.awsiot.mqttclient import MqttClient
from whirlpool.awsiot.oven import Oven
from whirlpool.oven import Cavity, CavityState, CookMode
from whirlpool.types import ApplianceInfo

CAPABILITIES = {
    "partNumber": "W11779688",
    "cavities": {
        "primaryCavity": {"cavityType": "oven"},
        "secondaryCavity": {"cavityType": "oven"},
    },
}

STATE = {
    "remoteStartEnable": True,
    "primaryCavity": {
        "cavityState": "idle",
        "doorStatus": "closed",
        "cavityLight": False,
        "ovenDisplayTemperature": 24.0,
        "targetTemperature": 0,
        "recipeID": "standby",
        "sessionId": "upper-session",
    },
    "secondaryCavity": {
        "cavityState": "cooking",
        "doorStatus": "open",
        "cavityLight": True,
        "ovenDisplayTemperature": 180.0,
        "targetTemperature": 176.7,
        "recipeID": "bake",
        "sessionId": "lower-session",
    },
}


def _oven() -> tuple[Oven, FakeMqttClient]:
    mqtt = FakeMqttClient()
    info = ApplianceInfo(
        said="OVEN1",
        name="My Oven",
        category="cooking",
        model_number="OVENMODEL1",
        serial_number="TEST",
    )
    oven = Oven(cast(MqttClient, mqtt), info, CAPABILITIES)
    oven.update_state(STATE)
    # Tests validate the immediate command. The delayed refresh behavior is
    # covered by the shared Appliance/MQTT tests and must not create sleepers.
    oven._schedule_state_refresh = lambda: None  # type: ignore[method-assign]
    return oven, mqtt


def _body(mqtt: FakeMqttClient) -> dict:
    return mqtt.published[-1][1]["payload"]


def test_two_cavities_and_state_getters() -> None:
    oven, _ = _oven()

    assert oven.get_oven_cavity_exists(Cavity.Upper)
    assert oven.get_oven_cavity_exists(Cavity.Lower)
    assert oven.get_cavity_state(Cavity.Upper) == CavityState.Standby
    assert oven.get_cavity_state(Cavity.Lower) == CavityState.Cooking
    assert oven.get_door_opened(Cavity.Upper) is False
    assert oven.get_door_opened(Cavity.Lower) is True
    assert oven.get_light(Cavity.Upper) is False
    assert oven.get_light(Cavity.Lower) is True
    assert oven.get_temp(Cavity.Lower) == 180.0
    assert oven.get_target_temp(Cavity.Lower) == 176.7
    assert oven.get_cook_mode(Cavity.Lower) == CookMode.Bake


async def test_light_command_uses_cavity_addressee() -> None:
    oven, mqtt = _oven()

    assert await oven.set_light(True, Cavity.Upper) is True
    assert _body(mqtt) == {
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
        (CookMode.SteamBake, "steamBake", 162.8),
        (CookMode.SlowCook, "slowCook", 121.1),
        (CookMode.ConvectSlowRoast4Hour, "convectSlowRoastLow", 135),
        (CookMode.ConvectSlowRoast8Hour, "convectSlowRoastMedium", 107.2),
        (CookMode.ConvectSlowRoast12Hour, "convectSlowRoastHigh", 93.3),
    ),
)
async def test_validated_recipe_payloads(
    mode: CookMode, recipe: str, target: float
) -> None:
    oven, mqtt = _oven()

    assert await oven.set_cook(target, mode, Cavity.Upper) is True
    assert _body(mqtt) == {
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
        (CookMode.FreshPizza, 250, 260),
        (CookMode.Proof, 32.22, 32.2),
        (CookMode.Proof, 37.78, 37.7),
    ),
)
async def test_discrete_temperature_recipes_snap_to_capability_values(
    mode: CookMode, requested: float, expected: float
) -> None:
    oven, mqtt = _oven()

    assert await oven.set_cook(requested, mode, Cavity.Upper) is True
    body = _body(mqtt)
    assert body["targetTemperature"] == expected
    assert "broilLevelTemperature" not in body
    assert "cookTimer" not in body


async def test_delay_start_uses_validated_delay_timer_shape() -> None:
    oven, mqtt = _oven()
    oven.stage_delay_start_minutes(30, Cavity.Upper)

    assert await oven.set_cook(176.7, CookMode.Bake, Cavity.Upper) is True
    assert _body(mqtt)["delayTimer"] == {"command": "run", "time": 1800}


async def test_fresh_pizza_rejects_delay() -> None:
    oven, mqtt = _oven()
    oven.stage_delay_start_minutes(30, Cavity.Upper)

    with pytest.raises(ValueError, match="does not support a delayed start"):
        await oven.set_cook(288, CookMode.FreshPizza, Cavity.Upper)

    assert mqtt.published == []


async def test_remote_start_disabled_prevents_cook_command() -> None:
    oven, mqtt = _oven()
    oven.update_state({"remoteStartEnable": False})

    assert await oven.set_cook(176.7, CookMode.Bake, Cavity.Upper) is False
    assert mqtt.published == []


async def test_stop_uses_session_id_when_reported() -> None:
    oven, mqtt = _oven()

    assert await oven.stop_cook(Cavity.Lower) is True
    assert _body(mqtt) == {
        "addressee": "secondaryCavity",
        "command": "cancel",
        "sessionId": "lower-session",
    }


def test_disconnected_presence_event_does_not_mark_oven_offline() -> None:
    oven, _ = _oven()

    oven.update_online(True)
    assert oven.get_online() is True
    oven.update_online(False)
    assert oven.get_online() is True


def test_unsupported_controls_remain_explicitly_unsupported() -> None:
    oven, _ = _oven()

    assert oven.get_kitchen_timer().get_state() is None
    assert oven.get_sabbath_mode() is None


def test_unvalidated_capability_honors_disconnected_presence() -> None:
    mqtt = FakeMqttClient()
    info = ApplianceInfo(
        said="OVEN2",
        name="Other Oven",
        category="cooking",
        model_number="OTHER",
        serial_number="TEST2",
    )
    capabilities = {
        "partNumber": "W99999999",
        "cavities": {"primaryCavity": {"cavityType": "oven"}},
    }
    oven = Oven(cast(MqttClient, mqtt), info, capabilities)

    oven.update_online(True)
    assert oven.get_online() is True
    oven.update_online(False)
    assert oven.get_online() is False


async def test_unvalidated_capability_does_not_claim_cook_control() -> None:
    mqtt = FakeMqttClient()
    info = ApplianceInfo(
        said="OVEN2",
        name="Other Oven",
        category="cooking",
        model_number="OTHER",
        serial_number="TEST2",
    )
    capabilities = {
        "partNumber": "W99999999",
        "cavities": {"primaryCavity": {"cavityType": "oven"}},
    }
    oven = Oven(cast(MqttClient, mqtt), info, capabilities)
    oven.update_state(
        {
            "remoteStartEnable": True,
            "primaryCavity": {"cavityState": "idle"},
        }
    )
    oven._schedule_state_refresh = lambda: None  # type: ignore[method-assign]

    assert oven.supports_cook_control is False
    assert await oven.set_cook(176.7, CookMode.Bake, Cavity.Upper) is False
    assert mqtt.published == []
