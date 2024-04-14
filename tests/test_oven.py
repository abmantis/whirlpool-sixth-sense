import asyncio
from unittest.mock import MagicMock

from whirlpool.oven import Cavity, CavityState, CookMode, Oven

from .aiohttp import AiohttpClientMocker
from .mock_backendselector import BackendSelectorMock
from .utils import (
    assert_appliance_setter_call,
    mock_appliance_http_get,
    mock_appliance_http_post,
)

ACCOUNT_ID = 111222333
SAID = "WPR1XYZABC123"
AC_NAME = "TestOv"

CURR_DIR = Path(__file__).parent
DATA_DIR = CURR_DIR / "data"

async def test_attributes(
    appliance_http_client_mock: AiohttpClientMocker,
    backend_selector_mock: BackendSelectorMock,
    auth_mock: MagicMock,
):
    mock_appliance_http_get(
        appliance_http_client_mock, backend_selector_mock, SAID, DATA1
    )
    appliance_http_client_mock.create_session(asyncio.get_event_loop())
    oven = Oven(
        backend_selector_mock, auth_mock, SAID, appliance_http_client_mock.session
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

    mock_appliance_http_get(
        appliance_http_client_mock, backend_selector_mock, SAID, DATA2
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
oven_data_file = DATA_DIR / "oven_data.json"
oven_data = json.loads(oven_data_file.read_text())

    mock_appliance_http_get(
        appliance_http_client_mock, backend_selector_mock, SAID, DATA3
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
    await appliance_http_client_mock.close_session()
DATA1 = oven_data["DATA1"]
DATA2 = oven_data["DATA2"]
DATA3 = oven_data["DATA3"]


async def test_setters(
    appliance_http_client_mock: AiohttpClientMocker,
    backend_selector_mock: BackendSelectorMock,
    auth_mock: MagicMock,
):
    mock_appliance_http_get(
        appliance_http_client_mock, backend_selector_mock, SAID, DATA2
    )
    mock_appliance_http_post(appliance_http_client_mock, backend_selector_mock)
    CONNECT_HTTP_CALLS = 2
    appliance_http_client_mock.create_session(asyncio.get_event_loop())
    oven = Oven(
        backend_selector_mock, auth_mock, SAID, appliance_http_client_mock.session
    )

    await oven.connect()
    await oven.set_control_locked(True)
    assert_appliance_setter_call(
        appliance_http_client_mock,
        SAID,
        {"Sys_OperationSetControlLock": "1"},
        CONNECT_HTTP_CALLS + 1,
    )

    await oven.set_control_locked(False)
    assert_appliance_setter_call(
        appliance_http_client_mock,
        SAID,
        {"Sys_OperationSetControlLock": "0"},
        CONNECT_HTTP_CALLS + 2,
    )

    await oven.set_light(True)
    assert_appliance_setter_call(
        appliance_http_client_mock,
        SAID,
        {"OvenUpperCavity_DisplaySetLightOn": "1"},
        CONNECT_HTTP_CALLS + 3,
    )

    await oven.set_cook(mode=CookMode.Bake, cavity=Cavity.Upper, target_temp=260)
    assert_appliance_setter_call(
        appliance_http_client_mock,
        SAID,
        {
            "OvenUpperCavity_CycleSetCommonMode": "2",
            "OvenUpperCavity_CycleSetTargetTemp": 2600,
            "OvenUpperCavity_OpSetOperations": 2,
        },
        CONNECT_HTTP_CALLS + 4,
    )

    await oven.set_bake(cavity=Cavity.Upper, target_temp=260)
    assert_appliance_setter_call(
        appliance_http_client_mock,
        SAID,
        {
            "OvenUpperCavity_CycleSetCommonMode": "2",
            "OvenUpperCavity_CycleSetTargetTemp": 2600,
            "OvenUpperCavity_OpSetOperations": 2,
        },
        CONNECT_HTTP_CALLS + 5,
    )

    await oven.set_cook(mode=CookMode.Broil, cavity=Cavity.Upper, target_temp=260)
    assert_appliance_setter_call(
        appliance_http_client_mock,
        SAID,
        {
            "OvenUpperCavity_CycleSetCommonMode": "8",
            "OvenUpperCavity_CycleSetTargetTemp": 2600,
            "OvenUpperCavity_OpSetOperations": 2,
        },
        CONNECT_HTTP_CALLS + 6,
    )

    await oven.set_broil(cavity=Cavity.Upper, target_temp=260)
    assert_appliance_setter_call(
        appliance_http_client_mock,
        SAID,
        {
            "OvenUpperCavity_CycleSetCommonMode": "8",
            "OvenUpperCavity_CycleSetTargetTemp": 2600,
            "OvenUpperCavity_OpSetOperations": 2,
        },
        CONNECT_HTTP_CALLS + 7,
    )

    await oven.set_convect_broil(cavity=Cavity.Upper, target_temp=260)
    assert_appliance_setter_call(
        appliance_http_client_mock,
        SAID,
        {
            "OvenUpperCavity_CycleSetCommonMode": "9",
            "OvenUpperCavity_CycleSetTargetTemp": 2600,
            "OvenUpperCavity_OpSetOperations": 2,
        },
        CONNECT_HTTP_CALLS + 8,
    )

    await oven.set_convect_bake(cavity=Cavity.Upper, target_temp=260)
    assert_appliance_setter_call(
        appliance_http_client_mock,
        SAID,
        {
            "OvenUpperCavity_CycleSetCommonMode": "6",
            "OvenUpperCavity_CycleSetTargetTemp": 2600,
            "OvenUpperCavity_OpSetOperations": 2,
        },
        CONNECT_HTTP_CALLS + 9,
    )

    await oven.set_keep_warm(cavity=Cavity.Upper, target_temp=100)
    assert_appliance_setter_call(
        appliance_http_client_mock,
        SAID,
        {
            "OvenUpperCavity_CycleSetCommonMode": "24",
            "OvenUpperCavity_CycleSetTargetTemp": 1000,
            "OvenUpperCavity_OpSetOperations": 2,
        },
        CONNECT_HTTP_CALLS + 10,
    )

    await oven.set_air_fry(cavity=Cavity.Upper, target_temp=260)
    assert_appliance_setter_call(
        appliance_http_client_mock,
        SAID,
        {
            "OvenUpperCavity_CycleSetCommonMode": "41",
            "OvenUpperCavity_CycleSetTargetTemp": 2600,
            "OvenUpperCavity_OpSetOperations": 2,
        },
        CONNECT_HTTP_CALLS + 11,
    )

    await oven.set_convect_roast(cavity=Cavity.Upper, target_temp=260)
    assert_appliance_setter_call(
        appliance_http_client_mock,
        SAID,
        {
            "OvenUpperCavity_CycleSetCommonMode": "16",
            "OvenUpperCavity_CycleSetTargetTemp": 2600,
            "OvenUpperCavity_OpSetOperations": 2,
        },
        CONNECT_HTTP_CALLS + 12,
    )

    await oven.stop_cook(Cavity.Upper)
    assert_appliance_setter_call(
        appliance_http_client_mock,
        SAID,
        {"OvenUpperCavity_OpSetOperations": 1},
        CONNECT_HTTP_CALLS + 13,
    )

    await oven.set_sabbath_mode(True)
    assert_appliance_setter_call(
        appliance_http_client_mock,
        SAID,
        {"Sys_OperationSetSabbathModeEnabled": "1"},
        CONNECT_HTTP_CALLS + 14,
    )

    await oven.set_display_brightness_percent(50)
    assert_appliance_setter_call(
        appliance_http_client_mock,
        SAID,
        {"Sys_DisplaySetBrightnessPercent": "50"},
        CONNECT_HTTP_CALLS + 15,
    )

    await oven.disconnect()
    await appliance_http_client_mock.close_session()
