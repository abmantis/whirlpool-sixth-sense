from collections.abc import Callable

import pytest
from aioresponses import aioresponses
from yarl import URL

from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.auth import Auth
from whirlpool.backendselector import BackendSelector
from whirlpool.oven import Cavity, CavityState, CookMode, Oven


async def test_attributes(appliances_manager: AppliancesManager):
    oven1 = appliances_manager.ovens[0]
    assert oven1.get_online() is True
    assert oven1.get_door_opened() is False
    assert oven1.get_control_locked() is False
    assert oven1.get_sabbath_mode() is False
    assert oven1.get_display_brightness_percent() == 90
    assert oven1.get_oven_cavity_exists(Cavity.Upper) is True
    assert oven1.get_oven_cavity_exists(Cavity.Lower) is False
    assert oven1.get_light(Cavity.Upper) is False
    assert oven1.get_meat_probe_status(Cavity.Upper) is False
    assert oven1.get_cook_time(Cavity.Upper) == 81
    assert oven1.get_temp(Cavity.Upper) == 37.7
    assert oven1.get_target_temp(Cavity.Upper) == 176.6
    assert oven1.get_cavity_state(Cavity.Upper) == CavityState.Preheating
    assert oven1.get_cook_mode(Cavity.Upper) == CookMode.Bake

    oven2 = appliances_manager.ovens[1]
    assert oven2.get_online() is True
    assert oven2.get_door_opened() is True
    assert oven2.get_control_locked() is True
    assert oven2.get_sabbath_mode() is False
    assert oven2.get_display_brightness_percent() == 70
    assert oven2.get_oven_cavity_exists(Cavity.Upper) is True
    assert oven2.get_oven_cavity_exists(Cavity.Lower) is False
    assert oven2.get_light(Cavity.Upper) is False
    assert oven2.get_meat_probe_status(Cavity.Upper) is False
    assert oven2.get_cook_time(Cavity.Upper) == 0
    assert oven2.get_temp(Cavity.Upper) == 0.0
    assert oven2.get_target_temp(Cavity.Upper) == 0.0
    assert oven2.get_cavity_state(Cavity.Upper) == CavityState.Standby
    assert oven2.get_cook_mode(Cavity.Upper) == CookMode.Standby

    oven3 = appliances_manager.ovens[2]
    assert oven3.get_online() is True
    assert oven3.get_door_opened() is False
    assert oven3.get_control_locked() is False
    assert oven3.get_sabbath_mode() is False
    assert oven3.get_display_brightness_percent() == 90
    assert oven3.get_oven_cavity_exists(Cavity.Upper) is True
    assert oven3.get_oven_cavity_exists(Cavity.Lower) is False
    assert oven3.get_light(Cavity.Upper) is False
    assert oven3.get_meat_probe_status(Cavity.Upper) is False
    assert oven3.get_cook_time(Cavity.Upper) == 0
    assert oven3.get_temp(Cavity.Upper) == 0.0
    assert oven3.get_target_temp(Cavity.Upper) == 0.0
    assert oven3.get_cavity_state(Cavity.Upper) == CavityState.Standby
    assert oven3.get_cook_mode(Cavity.Upper) == CookMode.Standby
    await appliances_manager.disconnect()


@pytest.mark.parametrize(
    ["method", "arguments", "expected_json"],
    [
        (Oven.set_control_locked, {"on": True}, {"Sys_OperationSetControlLock": "1"}),
        (Oven.set_control_locked, {"on": False}, {"Sys_OperationSetControlLock": "0"}),
        (Oven.set_light, {"on": True}, {"OvenUpperCavity_DisplaySetLightOn": "1"}),
        (
            Oven.set_cook,
            {"mode": CookMode.Bake, "cavity": Cavity.Upper, "target_temp": 260},
            {
                "OvenUpperCavity_CycleSetCommonMode": "2",
                "OvenUpperCavity_CycleSetTargetTemp": "2600",
                "OvenUpperCavity_OpSetOperations": "2",
            },
        ),
        (
            Oven.set_cook,
            {"mode": CookMode.Broil, "cavity": Cavity.Upper, "target_temp": 260},
            {
                "OvenUpperCavity_CycleSetCommonMode": "8",
                "OvenUpperCavity_CycleSetTargetTemp": "2600",
                "OvenUpperCavity_OpSetOperations": "2",
            },
        ),
        (
            Oven.set_cook,
            {"mode": CookMode.ConvectBroil, "cavity": Cavity.Upper, "target_temp": 260},
            {
                "OvenUpperCavity_CycleSetCommonMode": "9",
                "OvenUpperCavity_CycleSetTargetTemp": "2600",
                "OvenUpperCavity_OpSetOperations": "2",
            },
        ),
        (
            Oven.set_cook,
            {"mode": CookMode.ConvectBake, "cavity": Cavity.Upper, "target_temp": 260},
            {
                "OvenUpperCavity_CycleSetCommonMode": "6",
                "OvenUpperCavity_CycleSetTargetTemp": "2600",
                "OvenUpperCavity_OpSetOperations": "2",
            },
        ),
        (
            Oven.set_cook,
            {"mode": CookMode.KeepWarm, "cavity": Cavity.Upper, "target_temp": 100},
            {
                "OvenUpperCavity_CycleSetCommonMode": "24",
                "OvenUpperCavity_CycleSetTargetTemp": "1000",
                "OvenUpperCavity_OpSetOperations": "2",
            },
        ),
        (
            Oven.set_cook,
            {"mode": CookMode.AirFry, "cavity": Cavity.Upper, "target_temp": 260},
            {
                "OvenUpperCavity_CycleSetCommonMode": "41",
                "OvenUpperCavity_CycleSetTargetTemp": "2600",
                "OvenUpperCavity_OpSetOperations": "2",
            },
        ),
        (
            Oven.set_cook,
            {"mode": CookMode.ConvectRoast, "cavity": Cavity.Upper, "target_temp": 260},
            {
                "OvenUpperCavity_CycleSetCommonMode": "16",
                "OvenUpperCavity_CycleSetTargetTemp": "2600",
                "OvenUpperCavity_OpSetOperations": "2",
            },
        ),
        (
            Oven.stop_cook,
            {"cavity": Cavity.Upper},
            {"OvenUpperCavity_OpSetOperations": "1"},
        ),
        (
            Oven.set_sabbath_mode,
            {"on": True},
            {"Sys_OperationSetSabbathModeEnabled": "1"},
        ),
        (
            Oven.set_display_brightness_percent,
            {"pct": 50},
            {"Sys_DisplaySetBrightnessPercent": "50"},
        ),
    ],
)
async def test_setters(
    appliances_manager: AppliancesManager,
    auth: Auth,
    backend_selector: BackendSelector,
    aioresponses_mock: aioresponses,
    method: Callable,
    arguments: dict,
    expected_json: dict,
):
    oven = appliances_manager.ovens[0]
    expected_payload = {
        "json": {
            "body": expected_json,
            "header": {"said": oven.said, "command": "setAttributes"},
        }
    }

    post_request_call_kwargs = {
        "url": backend_selector.appliance_command_url,
        "method": "POST",
        "data": None,
        "json": expected_payload["json"],
        "allow_redirects": True,
        "headers": auth.create_headers(),
    }

    url = backend_selector.appliance_command_url

    # add call, call method
    aioresponses_mock.post(url, payload=expected_payload)
    assert await method(oven, **arguments)

    # assert args and length
    aioresponses_mock.assert_called_with(**post_request_call_kwargs)
    assert len(aioresponses_mock.requests[("POST", URL(url))]) == 1
