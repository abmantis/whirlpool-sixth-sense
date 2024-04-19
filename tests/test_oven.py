import json
from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from yarl import URL

from whirlpool.oven import Cavity, CavityState, CookMode, Oven

ACCOUNT_ID = 111222333
SAID = "WPR1XYZABC123"
AC_NAME = "TestOv"

CURR_DIR = Path(__file__).parent
DATA_DIR = CURR_DIR / "data"

oven_data_file = DATA_DIR / "oven_data.json"
oven_data = json.loads(oven_data_file.read_text())

DATA1 = oven_data["DATA1"]
DATA2 = oven_data["DATA2"]
DATA3 = oven_data["DATA3"]


async def test_attributes(auth_mock, aioresponses_mock):
    oven = Oven(auth_mock._backend_selector, auth_mock, SAID, auth_mock._session)

    aioresponses_mock.get(
        auth_mock._backend_selector.websocket_url,
        payload={"url": "wss://something"},
        repeat=True,
    )

    aioresponses_mock.get(
        auth_mock._backend_selector.get_appliance_data_url(SAID), payload=DATA1
    )
    await oven.connect()
    assert oven.get_online() is True
    assert oven.get_door_opened() == False
    assert oven.get_control_locked() == False
    assert oven.get_sabbath_mode() == False
    assert oven.get_display_brightness_percent() == 90
    assert oven.get_oven_cavity_exists(Cavity.Upper) == True
    assert oven.get_oven_cavity_exists(Cavity.Lower) == False
    assert oven.get_light(Cavity.Upper) == False
    assert oven.get_meat_probe_status(Cavity.Upper) == False
    assert oven.get_cook_time(Cavity.Upper) == 81
    assert oven.get_temp(Cavity.Upper) == 37.7
    assert oven.get_target_temp(Cavity.Upper) == 176.6
    assert oven.get_cavity_state(Cavity.Upper) == CavityState.Preheating
    assert oven.get_cook_mode(Cavity.Upper) == CookMode.Bake
    await oven.disconnect()

    aioresponses_mock.get(
        auth_mock._backend_selector.get_appliance_data_url(SAID), payload=DATA2
    )
    await oven.connect()
    assert oven.get_online() is True
    assert oven.get_door_opened() == True
    assert oven.get_control_locked() == True
    assert oven.get_sabbath_mode() == False
    assert oven.get_display_brightness_percent() == 70
    assert oven.get_oven_cavity_exists(Cavity.Upper) == True
    assert oven.get_oven_cavity_exists(Cavity.Lower) == False
    assert oven.get_light(Cavity.Upper) == False
    assert oven.get_meat_probe_status(Cavity.Upper) == False
    assert oven.get_cook_time(Cavity.Upper) == 0
    assert oven.get_temp(Cavity.Upper) == 0.0
    assert oven.get_target_temp(Cavity.Upper) == 0.0
    assert oven.get_cavity_state(Cavity.Upper) == CavityState.Standby
    assert oven.get_cook_mode(Cavity.Upper) == CookMode.Standby
    await oven.disconnect()

    aioresponses_mock.get(
        auth_mock._backend_selector.get_appliance_data_url(SAID), payload=DATA3
    )
    await oven.connect()
    assert oven.get_online() is True
    assert oven.get_door_opened() == False
    assert oven.get_control_locked() == False
    assert oven.get_sabbath_mode() == False
    assert oven.get_display_brightness_percent() == 90
    assert oven.get_oven_cavity_exists(Cavity.Upper) == True
    assert oven.get_oven_cavity_exists(Cavity.Lower) == False
    assert oven.get_light(Cavity.Upper) == False
    assert oven.get_meat_probe_status(Cavity.Upper) == False
    assert oven.get_cook_time(Cavity.Upper) == 0
    assert oven.get_temp(Cavity.Upper) == 0.0
    assert oven.get_target_temp(Cavity.Upper) == 0.0
    assert oven.get_cavity_state(Cavity.Upper) == CavityState.Standby
    assert oven.get_cook_mode(Cavity.Upper) == CookMode.Standby
    await oven.disconnect()


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
                "OvenUpperCavity_CycleSetTargetTemp": 2600,
                "OvenUpperCavity_OpSetOperations": 2,
            },
        ),
        (
            Oven.set_bake,
            {"cavity": Cavity.Upper, "target_temp": 260},
            {
                "OvenUpperCavity_CycleSetCommonMode": "2",
                "OvenUpperCavity_CycleSetTargetTemp": 2600,
                "OvenUpperCavity_OpSetOperations": 2,
            },
        ),
        (
            Oven.set_cook,
            {"mode": CookMode.Broil, "cavity": Cavity.Upper, "target_temp": 260},
            {
                "OvenUpperCavity_CycleSetCommonMode": "8",
                "OvenUpperCavity_CycleSetTargetTemp": 2600,
                "OvenUpperCavity_OpSetOperations": 2,
            },
        ),
        (
            Oven.set_broil,
            {"cavity": Cavity.Upper, "target_temp": 260},
            {
                "OvenUpperCavity_CycleSetCommonMode": "8",
                "OvenUpperCavity_CycleSetTargetTemp": 2600,
                "OvenUpperCavity_OpSetOperations": 2,
            },
        ),
        (
            Oven.set_convect_broil,
            {"cavity": Cavity.Upper, "target_temp": 260},
            {
                "OvenUpperCavity_CycleSetCommonMode": "9",
                "OvenUpperCavity_CycleSetTargetTemp": 2600,
                "OvenUpperCavity_OpSetOperations": 2,
            },
        ),
        (
            Oven.set_convect_bake,
            {"cavity": Cavity.Upper, "target_temp": 260},
            {
                "OvenUpperCavity_CycleSetCommonMode": "6",
                "OvenUpperCavity_CycleSetTargetTemp": 2600,
                "OvenUpperCavity_OpSetOperations": 2,
            },
        ),
        (
            Oven.set_keep_warm,
            {"cavity": Cavity.Upper, "target_temp": 100},
            {
                "OvenUpperCavity_CycleSetCommonMode": "24",
                "OvenUpperCavity_CycleSetTargetTemp": 1000,
                "OvenUpperCavity_OpSetOperations": 2,
            },
        ),
        (
            Oven.set_air_fry,
            {"cavity": Cavity.Upper, "target_temp": 260},
            {
                "OvenUpperCavity_CycleSetCommonMode": "41",
                "OvenUpperCavity_CycleSetTargetTemp": 2600,
                "OvenUpperCavity_OpSetOperations": 2,
            },
        ),
        (
            Oven.set_convect_roast,
            {"cavity": Cavity.Upper, "target_temp": 260},
            {
                "OvenUpperCavity_CycleSetCommonMode": "16",
                "OvenUpperCavity_CycleSetTargetTemp": 2600,
                "OvenUpperCavity_OpSetOperations": 2,
            },
        ),
        (
            Oven.stop_cook,
            {"cavity": Cavity.Upper},
            {"OvenUpperCavity_OpSetOperations": 1},
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
    auth_mock, aioresponses_mock, method: Callable, arguments: dict, expected_json: dict
):
    expected_payload = {
        "json": {
            "body": expected_json,
            "header": {"said": SAID, "command": "setAttributes"},
        }
    }

    call_kwargs = {
        "url": auth_mock._backend_selector.appliance_command_url,
        "method": "POST",
        "data": None,
        "json": expected_payload["json"],
        "allow_redirects": True,
        "headers": {},
    }

    with patch("whirlpool.appliance.Appliance._create_headers", return_value={}):
        oven = Oven(auth_mock._backend_selector, auth_mock, SAID, auth_mock._session)
        url = auth_mock._backend_selector.appliance_command_url

        aioresponses_mock.get(
            auth_mock._backend_selector.websocket_url,
            payload={"url": "wss://something"},
        )
        aioresponses_mock.get(
            auth_mock._backend_selector.get_appliance_data_url(SAID), payload=DATA2
        )

        await oven.connect()

        # add call, call method
        aioresponses_mock.post(url, payload=expected_payload)
        await method(oven, **arguments)

        # assert args and length
        aioresponses_mock.assert_called_with(**call_kwargs)
        assert len(aioresponses_mock.requests[("POST", URL(url))]) == 1

        await oven.disconnect()
