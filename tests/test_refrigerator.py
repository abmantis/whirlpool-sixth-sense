import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from yarl import URL

from whirlpool.backendselector import BackendSelector
from whirlpool.refrigerator import Refrigerator

ACCOUNT_ID = 111222333


CURR_DIR = Path(__file__).parent
DATA_DIR = CURR_DIR / "data"

REFRIGERATOR_DATA = json.loads((DATA_DIR / "refrigerator_data.json").read_text())

DATA1 = REFRIGERATOR_DATA["DATA1"]
DATA2 = REFRIGERATOR_DATA["DATA2"]


async def test_attributes(
    refrigerator: Refrigerator,
    backend_selector_mock: BackendSelector,
    aioresponses_mock,
):
    aioresponses_mock.get(
        backend_selector_mock.websocket_url,
        payload={"url": "wss://something"},
        repeat=True,
    )
    aioresponses_mock.get(
        backend_selector_mock.get_appliance_data_url(refrigerator.said), payload=DATA1
    )

    await refrigerator.connect()
    assert refrigerator.get_online() is False
    assert refrigerator.get_offset_temp() == "0"
    assert refrigerator.get_turbo_mode() is False
    assert refrigerator.get_display_lock() is False
    await refrigerator.disconnect()

    aioresponses_mock.get(
        backend_selector_mock.get_appliance_data_url(refrigerator.said), payload=DATA2
    )

    await refrigerator.connect()
    assert refrigerator.get_online() is True
    assert refrigerator.get_turbo_mode() is True
    assert refrigerator.get_display_lock() is True
    assert refrigerator.get_offset_temp() == "5"
    await refrigerator.disconnect()


@pytest.mark.parametrize(
    ["method", "argument", "expected_json"],
    [
        (Refrigerator.set_offset_temp, -4, {"Refrigerator_OpSetTempPreset": "12"}),
        (Refrigerator.set_offset_temp, -2, {"Refrigerator_OpSetTempPreset": "11"}),
        (Refrigerator.set_offset_temp, 0, {"Refrigerator_OpSetTempPreset": "10"}),
        (Refrigerator.set_offset_temp, 3, {"Refrigerator_OpSetTempPreset": "9"}),
        (Refrigerator.set_offset_temp, 5, {"Refrigerator_OpSetTempPreset": "8"}),
        (Refrigerator.set_temp, 8, {"Refrigerator_OpSetTempPreset": "8"}),
        (Refrigerator.set_temp, 12, {"Refrigerator_OpSetTempPreset": "12"}),
        (Refrigerator.set_turbo_mode, True, {"Sys_OpSetMaxCool": "1"}),
        (Refrigerator.set_turbo_mode, False, {"Sys_OpSetMaxCool": "0"}),
        (Refrigerator.set_display_lock, True, {"Sys_OpSetControlLock": "1"}),
        (Refrigerator.set_display_lock, False, {"Sys_OpSetControlLock": "0"}),
    ],
)
async def test_setters(
    refrigerator: Refrigerator,
    backend_selector_mock: BackendSelector,
    aioresponses_mock,
    method: Callable,
    argument: Any,
    expected_json: dict,
):
    expected_payload = {
        "json": {
            "body": expected_json,
            "header": {"said": refrigerator.said, "command": "setAttributes"},
        }
    }

    post_request_call_kwargs = {
        "url": backend_selector_mock.appliance_command_url,
        "method": "POST",
        "data": None,
        "json": expected_payload["json"],
        "allow_redirects": True,
        "headers": {},
    }

    url = backend_selector_mock.appliance_command_url

    aioresponses_mock.get(
        backend_selector_mock.websocket_url, payload={"url": "wss://something"}
    )
    aioresponses_mock.get(
        backend_selector_mock.get_appliance_data_url(refrigerator.said), payload=DATA1
    )

    await refrigerator.connect()

    # add call, call method
    aioresponses_mock.post(url, payload=expected_payload)
    await method(refrigerator, argument)

    # assert args and length
    aioresponses_mock.assert_called_with(**post_request_call_kwargs)
    assert len(aioresponses_mock.requests[("POST", URL(url))]) == 1

    await refrigerator.disconnect()
