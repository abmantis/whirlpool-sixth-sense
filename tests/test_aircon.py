from collections.abc import Callable
from typing import Any

import pytest
from aioresponses import aioresponses
from yarl import URL

from whirlpool.aircon import Aircon, FanSpeed, Mode
from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.auth import Auth
from whirlpool.backendselector import BackendSelector


async def test_attributes(appliances_manager: AppliancesManager):
    aircon1 = appliances_manager.aircons[0]

    assert aircon1.get_online() is False
    assert aircon1.get_power_on() is False
    assert aircon1.get_display_on() is False
    assert aircon1.get_current_temp() == 23
    assert aircon1.get_current_humidity() == 56
    assert aircon1.get_temp() == 30
    assert aircon1.get_humidity() == 40
    assert aircon1.get_mode() == Mode.Heat
    assert aircon1.get_sixthsense_mode() is False
    assert aircon1.get_fanspeed() == FanSpeed.Off
    assert aircon1.get_h_louver_swing() is True
    assert aircon1.get_turbo_mode() is False
    assert aircon1.get_eco_mode() is False
    assert aircon1.get_quiet_mode() is False

    aircon2 = appliances_manager.aircons[1]
    assert aircon2.get_online() is True
    assert aircon2.get_power_on() is True
    assert aircon2.get_display_on() is True
    assert aircon2.get_current_temp() == 30
    assert aircon2.get_current_humidity() == 31
    assert aircon2.get_temp() == 29
    assert aircon2.get_humidity() == 45
    assert aircon2.get_mode() == Mode.Fan
    assert aircon2.get_sixthsense_mode() is True
    assert aircon2.get_fanspeed() == FanSpeed.Auto
    assert aircon2.get_h_louver_swing() is False
    assert aircon2.get_turbo_mode() is True
    assert aircon2.get_eco_mode() is True
    assert aircon2.get_quiet_mode() is True


@pytest.mark.parametrize(
    ["method", "argument", "expected_json"],
    [
        (Aircon.set_power_on, True, {"Sys_OpSetPowerOn": "1"}),
        (Aircon.set_power_on, False, {"Sys_OpSetPowerOn": "0"}),
        (Aircon.set_temp, 30, {"Sys_OpSetTargetTemp": "300"}),
        (Aircon.set_humidity, 45, {"Sys_OpSetTargetHumidity": "45"}),
        (Aircon.set_mode, Mode.Cool, {"Cavity_OpSetMode": "1"}),
        (Aircon.set_fanspeed, FanSpeed.Auto, {"Cavity_OpSetFanSpeed": "1"}),
        (Aircon.set_h_louver_swing, True, {"Cavity_OpSetHorzLouverSwing": "1"}),
        (Aircon.set_turbo_mode, False, {"Cavity_OpSetTurboMode": "0"}),
        (Aircon.set_eco_mode, False, {"Sys_OpSetEcoModeEnabled": "0"}),
        (Aircon.set_quiet_mode, False, {"Sys_OpSetQuietModeEnabled": "0"}),
        (Aircon.set_display_on, True, {"Sys_DisplaySetBrightness": "4"}),
    ],
)
async def test_setters(
    appliances_manager: AppliancesManager,
    auth: Auth,
    backend_selector: BackendSelector,
    aioresponses_mock: aioresponses,
    method: Callable,
    argument: Any,
    expected_json: dict,
):
    aircon = appliances_manager.aircons[0]
    expected_payload = {
        "json": {
            "body": expected_json,
            "header": {"said": aircon.said, "command": "setAttributes"},
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
    assert await method(aircon, argument)

    # assert args and length
    aioresponses_mock.assert_called_with(**post_request_call_kwargs)
    assert len(aioresponses_mock.requests[("POST", URL(url))]) == 1


@pytest.mark.parametrize(
    ["method", "argument", "message"],
    [
        (Aircon.set_mode, "Invalid Mode", "Invalid mode"),
        (Aircon.set_fanspeed, "Invalid speed", "Invalid fan speed"),
    ],
)
async def test_setters_invalid_arg(
    appliances_manager: AppliancesManager,
    method: Callable,
    argument: Any,
    message: str,
):
    aircon = appliances_manager.aircons[0]
    with pytest.raises(ValueError) as exc_info:
        await method(aircon, argument)

    assert message in str(exc_info.value)
