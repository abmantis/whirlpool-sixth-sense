import json
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import aiohttp
import pytest
from aioresponses import aioresponses
from yarl import URL

from whirlpool.aircon import Aircon, FanSpeed, Mode

from .mock_backendselector import BackendSelectorMock

ACCOUNT_ID = 111222333
SAID = "WPR1XYZABC123"
AC_NAME = "TestAc"


CURR_DIR = Path(__file__).parent
DATA_DIR = CURR_DIR / "data"

aircon_data_file = DATA_DIR / "aircon_data.json"
aircon_data = json.loads(aircon_data_file.read_text())

DATA1 = aircon_data["DATA1"]
DATA2 = aircon_data["DATA2"]


async def test_attributes():
    backend_selector_mock = BackendSelectorMock()
    session = aiohttp.ClientSession()
    aircon = Aircon(
        backend_selector_mock,
        MagicMock(),
        SAID,
        session,
    )
    with aioresponses() as m:
        m.get(
            backend_selector_mock.websocket_url,
            payload={"url": "wss://something"},
            repeat=True,
        )
        m.get(backend_selector_mock.get_appliance_data_url(SAID), payload=DATA1)

        await aircon.connect()
        assert aircon.get_online() is False
        assert aircon.get_power_on() is False
        assert aircon.get_display_on() is False
        assert aircon.get_current_temp() == 23
        assert aircon.get_current_humidity() == 56
        assert aircon.get_temp() == 30
        assert aircon.get_humidity() == 40
        assert aircon.get_mode() == Mode.Heat
        assert aircon.get_sixthsense_mode() is False
        assert aircon.get_fanspeed() == FanSpeed.Off
        assert aircon.get_h_louver_swing() is True
        assert aircon.get_turbo_mode() is False
        assert aircon.get_eco_mode() is False
        assert aircon.get_quiet_mode() is False
        await aircon.disconnect()

        m.get(backend_selector_mock.get_appliance_data_url(SAID), payload=DATA2)

        await aircon.connect()
        assert aircon.get_online() is True
        assert aircon.get_power_on() is True
        assert aircon.get_display_on() is True
        assert aircon.get_current_temp() == 30
        assert aircon.get_current_humidity() == 31
        assert aircon.get_temp() == 29
        assert aircon.get_humidity() == 45
        assert aircon.get_mode() == Mode.Fan
        assert aircon.get_sixthsense_mode() is True
        assert aircon.get_fanspeed() == FanSpeed.Auto
        assert aircon.get_h_louver_swing() is False
        assert aircon.get_turbo_mode() is True
        assert aircon.get_eco_mode() is True
        assert aircon.get_quiet_mode() is True
        await aircon.disconnect()

    await session.close()


@pytest.mark.parametrize(
    ["method", "argument", "expected"],
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
async def test_setters(method: Callable, argument: Any, expected: dict):
    backend_selector_mock = BackendSelectorMock()
    expected_template = {
        "json": {
            "body": expected,
            "header": {"said": SAID, "command": "setAttributes"},
        }
    }

    call_kwargs = {
        "url": backend_selector_mock.appliance_command_url,
        "method": "POST",
        "data": None,
        "json": expected_template["json"],
        "allow_redirects": True,
        "headers": {},
    }

    with patch("whirlpool.appliance.Appliance._create_headers", return_value={}):
        session = aiohttp.ClientSession()
        aircon = Aircon(backend_selector_mock, MagicMock(), SAID, session)
        url = backend_selector_mock.appliance_command_url

        with aioresponses() as m:
            m.get(
                backend_selector_mock.websocket_url, payload={"url": "wss://something"}
            )
            m.get(backend_selector_mock.get_appliance_data_url(SAID), payload=DATA1)

            await aircon.connect()

            # add call, call method
            m.post(url, payload=expected_template)
            await method(aircon, argument)

            # assert args and length
            m.assert_called_with(**call_kwargs)
            assert len(m.requests[("POST", URL(url))]) == 1

            await aircon.disconnect()

        await session.close()
