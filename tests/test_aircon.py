from unittest.mock import MagicMock

from whirlpool.aircon import Aircon, FanSpeed, Mode

from .aiohttp import AiohttpClientMocker
from .mock_backendselector import BackendSelectorMock

ACCOUNT_ID = 111222333
SAID = "WPR1XYZABC123"
AC_NAME = "TestAc"
DATA1 = {
    "_id": SAID,
    "applianceId": SAID,
    "lastFullSyncTime": 1604500393149,
    "lastModified": 1641436766989,
    "attributes": {
        "Cavity_OpSetFanSpeed": {"value": "0", "updateTime": 1626535975892},
        "Cavity_OpSetHorzLouverSwing": {"value": "1", "updateTime": 1626517992782},
        "Cavity_OpSetMode": {"value": "3", "updateTime": 1626535966896},
        "Cavity_OpSetTurboMode": {"value": "0", "updateTime": 1626517785042},
        "Cavity_OpStatusMode": {"value": "3", "updateTime": 1626535966896},
        "Online": {"value": "0", "updateTime": 1626536325968},
        "SAID": {"value": SAID, "updateTime": 1626517782012},
        "Sys_DisplaySetBrightness": {"value": "0", "updateTime": 1626535966896},
        "Sys_OpSetEcoModeEnabled": {"value": "0", "updateTime": 1626517785042},
        "Sys_OpSetPowerOn": {"value": "0", "updateTime": 1626535966896},
        "Sys_OpSetQuietModeEnabled": {"value": "0", "updateTime": 1626517785042},
        "Sys_OpSetSleepMode": {"value": "0", "updateTime": 1626517785042},
        "Sys_OpSetTargetHumidity": {"value": "40", "updateTime": 1626517785042},
        "Sys_OpSetTargetTemp": {"value": "300", "updateTime": 1626535966896},
        "Sys_OpStatusDisplayHumidity": {"value": "56", "updateTime": 1626536203199},
        "Sys_OpStatusDisplayTemp": {"value": "230", "updateTime": 1626535909593},
    },
}
DATA2 = {
    "_id": SAID,
    "applianceId": SAID,
    "lastFullSyncTime": 1604500393149,
    "lastModified": 1641436766989,
    "attributes": {
        "Cavity_OpSetFanSpeed": {"value": "1", "updateTime": 1626535975892},
        "Cavity_OpSetHorzLouverSwing": {"value": "0", "updateTime": 1626517992782},
        "Cavity_OpSetMode": {"value": "4", "updateTime": 1626535966896},
        "Cavity_OpSetTurboMode": {"value": "1", "updateTime": 1626517785042},
        "Cavity_OpStatusMode": {"value": "2", "updateTime": 1626535966896},
        "Online": {"value": "1", "updateTime": 1626536325968},
        "SAID": {"value": SAID, "updateTime": 1626517782012},
        "Sys_DisplaySetBrightness": {"value": "4", "updateTime": 1626535966896},
        "Sys_OpSetEcoModeEnabled": {"value": "1", "updateTime": 1626517785042},
        "Sys_OpSetPowerOn": {"value": "1", "updateTime": 1626535966896},
        "Sys_OpSetQuietModeEnabled": {"value": "1", "updateTime": 1626517785042},
        "Sys_OpSetSleepMode": {"value": "1", "updateTime": 1626517785042},
        "Sys_OpSetTargetHumidity": {"value": "45", "updateTime": 1626517785042},
        "Sys_OpSetTargetTemp": {"value": "290", "updateTime": 1626535966896},
        "Sys_OpStatusDisplayHumidity": {"value": "31", "updateTime": 1626536203199},
        "Sys_OpStatusDisplayTemp": {"value": "300", "updateTime": 1626535909593},
    },
}


async def test_attributes(
    appliance_http_client_mock: AiohttpClientMocker,
    backend_selector_mock: BackendSelectorMock,
    auth_mock: MagicMock,
):
    appliance_http_client_mock.get(
        f"{backend_selector_mock.base_url}/api/v1/appliance/{SAID}",
        json=DATA1,
    )

    aircon = Aircon(backend_selector_mock, auth_mock, SAID)
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

    appliance_http_client_mock.get(
        f"{backend_selector_mock.base_url}/api/v1/appliance/{SAID}",
        json=DATA2,
    )
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

    # TODO: update DATA with changed attributes for things that are not tested yet


async def test_setters(
    appliance_http_client_mock: AiohttpClientMocker,
    backend_selector_mock: BackendSelectorMock,
    auth_mock: MagicMock,
):
    appliance_http_client_mock.get(
        f"{backend_selector_mock.base_url}/api/v1/appliance/{SAID}",
        json=DATA1,
    )
    appliance_http_client_mock.post(
        f"{backend_selector_mock.base_url}/api/v1/appliance/command"
    )

    def assert_setter_call(expected_data_body, call_count):
        expected_cmd_data_base = {
            "header": {"said": SAID, "command": "setAttributes"},
        }
        mock_calls = appliance_http_client_mock.mock_calls
        assert len(mock_calls) == call_count
        assert mock_calls[-1][0] == "POST"
        assert mock_calls[-1][1].path == "/api/v1/appliance/command"
        assert mock_calls[-1][2] == expected_cmd_data_base | {
            "body": expected_data_body
        }

    aircon = Aircon(backend_selector_mock, auth_mock, SAID)
    await aircon.connect()

    await aircon.set_power_on(True)
    assert_setter_call({"Sys_OpSetPowerOn": "1"}, 3)

    await aircon.set_power_on(False)
    assert_setter_call({"Sys_OpSetPowerOn": "0"}, 4)

    await aircon.set_temp(30)
    assert_setter_call({"Sys_OpSetTargetTemp": "300"}, 5)

    await aircon.set_humidity(45)
    assert_setter_call({"Sys_OpSetTargetHumidity": "45"}, 6)

    await aircon.set_mode(Mode.Cool)
    assert_setter_call({"Cavity_OpSetMode": "1"}, 7)

    await aircon.set_fanspeed(FanSpeed.Auto)
    assert_setter_call({"Cavity_OpSetFanSpeed": "1"}, 8)

    await aircon.set_h_louver_swing(True)
    assert_setter_call({"Cavity_OpSetHorzLouverSwing": "1"}, 9)

    await aircon.set_turbo_mode(False)
    assert_setter_call({"Cavity_OpSetTurboMode": "0"}, 10)

    await aircon.set_eco_mode(False)
    assert_setter_call({"Sys_OpSetEcoModeEnabled": "0"}, 11)

    await aircon.set_quiet_mode(False)
    assert_setter_call({"Sys_OpSetQuietModeEnabled": "0"}, 12)

    await aircon.set_display_on(True)
    assert_setter_call({"Sys_DisplaySetBrightness": "4"}, 13)

    await aircon.disconnect()
