import json
import logging
import pytest
from unittest.mock import ANY, MagicMock
from tests.mock_backendselector import BackendSelectorMock

from whirlpool.aircon import Aircon, FanSpeed, Mode

from . import MockResponse


pytestmark = pytest.mark.asyncio

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


def get_request_side_effect(url):
    if url.endswith("/getUserDetails"):
        return MockResponse(
            json.dumps(
                {
                    "accountId": ACCOUNT_ID,
                    "firstName": "Test",
                    "lastName": "Dummy",
                    "email": "testdummy@testing.com",
                }
            ),
            200,
        )
    if url.endswith(f"/appliancebyaccount/{ACCOUNT_ID}"):
        return MockResponse(
            json.dumps(
                {ACCOUNT_ID: {"12345": [{"APPLIANCE_NAME": AC_NAME, "SAID": SAID}]}}
            ),
            200,
        )
    if url.endswith(f"/appliance/{SAID}"):
        return MockResponse(json.dumps({}), 200)

    raise Exception(f"Unexpected url: {url}")


async def test_attributes(caplog, aio_httpclient):
    caplog.set_level(logging.DEBUG)
    auth = MagicMock()

    aio_httpclient.get.return_value = MockResponse(json.dumps(DATA1), 200)

    aircon = Aircon(BackendSelectorMock(), auth, SAID, None)
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

    aio_httpclient.get.return_value = MockResponse(json.dumps(DATA2), 200)
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


async def test_setters(caplog, aio_httpclient):
    caplog.set_level(logging.DEBUG)
    auth = MagicMock()

    aio_httpclient.get.return_value = MockResponse(json.dumps(DATA1), 200)
    aio_httpclient.post.return_value = MockResponse("", 200)

    cmd_data = {
        "header": {"said": SAID, "command": "setAttributes"},
    }

    aircon = Aircon(BackendSelectorMock(), auth, SAID, None)
    await aircon.connect()
    await aircon.set_power_on(True)
    cmd_data["body"] = {"Sys_OpSetPowerOn": "1"}
    aio_httpclient.post.assert_called_once_with(ANY, json=cmd_data)

    aio_httpclient.post.reset_mock()
    await aircon.set_power_on(False)
    cmd_data["body"] = {"Sys_OpSetPowerOn": "0"}
    aio_httpclient.post.assert_called_once_with(ANY, json=cmd_data)

    aio_httpclient.post.reset_mock()
    await aircon.set_temp(30)
    cmd_data["body"] = {"Sys_OpSetTargetTemp": "300"}
    aio_httpclient.post.assert_called_once_with(ANY, json=cmd_data)

    aio_httpclient.post.reset_mock()
    await aircon.set_humidity(45)
    cmd_data["body"] = {"Sys_OpSetTargetHumidity": "45"}
    aio_httpclient.post.assert_called_once_with(ANY, json=cmd_data)

    aio_httpclient.post.reset_mock()
    await aircon.set_mode(Mode.Cool)
    cmd_data["body"] = {"Cavity_OpSetMode": "1"}
    aio_httpclient.post.assert_called_once_with(ANY, json=cmd_data)

    aio_httpclient.post.reset_mock()
    await aircon.set_fanspeed(FanSpeed.Auto)
    cmd_data["body"] = {"Cavity_OpSetFanSpeed": "1"}
    aio_httpclient.post.assert_called_once_with(ANY, json=cmd_data)

    aio_httpclient.post.reset_mock()
    await aircon.set_h_louver_swing(True)
    cmd_data["body"] = {"Cavity_OpSetHorzLouverSwing": "1"}
    aio_httpclient.post.assert_called_once_with(ANY, json=cmd_data)

    aio_httpclient.post.reset_mock()
    await aircon.set_turbo_mode(False)
    cmd_data["body"] = {"Cavity_OpSetTurboMode": "0"}
    aio_httpclient.post.assert_called_once_with(ANY, json=cmd_data)

    aio_httpclient.post.reset_mock()
    await aircon.set_eco_mode(False)
    cmd_data["body"] = {"Sys_OpSetEcoModeEnabled": "0"}
    aio_httpclient.post.assert_called_once_with(ANY, json=cmd_data)

    aio_httpclient.post.reset_mock()
    await aircon.set_quiet_mode(False)
    cmd_data["body"] = {"Sys_OpSetQuietModeEnabled": "0"}
    aio_httpclient.post.assert_called_once_with(ANY, json=cmd_data)

    aio_httpclient.post.reset_mock()
    await aircon.set_display_on(True)
    cmd_data["body"] = {"Sys_DisplaySetBrightness": "4"}
    aio_httpclient.post.assert_called_once_with(ANY, json=cmd_data)

    await aircon.disconnect()
