from collections.abc import Callable
from typing import Any

import pytest
from aiointercept import aiointercept
from yarl import URL

from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.auth import Auth
from whirlpool.backendselector import BackendSelector
from whirlpool.refrigerator import Refrigerator


async def test_attributes(appliances_manager: AppliancesManager):
    refrigerator1 = appliances_manager.refrigerators[0]
    assert refrigerator1.get_online() is False
    assert refrigerator1.get_offset_temp() == 0
    assert refrigerator1.get_turbo_mode() is False
    assert refrigerator1.get_display_lock() is False

    refrigerator2 = appliances_manager.refrigerators[1]
    assert refrigerator2.get_online() is True
    assert refrigerator2.get_turbo_mode() is True
    assert refrigerator2.get_display_lock() is True
    assert refrigerator2.get_offset_temp() == 5


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
    appliances_manager: AppliancesManager,
    auth: Auth,
    backend_selector: BackendSelector,
    aiointercept_mock: aiointercept,
    method: Callable,
    argument: Any,
    expected_json: dict,
):
    refrigerator = appliances_manager.refrigerators[0]

    expected_payload = {
        "json": {
            "body": expected_json,
            "header": {"said": refrigerator.said, "command": "setAttributes"},
        }
    }

    post_request_call_kwargs = {
        "url": backend_selector.appliance_command_url,
        "method": "POST",
        "data": None,
        "json": expected_payload["json"],
        "headers": auth.create_headers(),
    }

    url = backend_selector.appliance_command_url

    # add call, call method
    aiointercept_mock.post(url, payload=expected_payload)
    await getattr(refrigerator, method.__name__)(argument)

    # assert args and length
    aiointercept_mock.assert_called_with(**post_request_call_kwargs)
    assert len(aiointercept_mock.requests[("POST", URL(url))]) == 1


@pytest.mark.parametrize(
    ["method", "argument", "message"],
    [
        (Refrigerator.set_offset_temp, 1, "Invalid temperature: 1"),
        (Refrigerator.set_offset_temp, 4, "Invalid temperature: 4"),
        (Refrigerator.set_offset_temp, 6, "Invalid temperature: 6"),
        (Refrigerator.set_temp, 7, "Invalid temperature: 7"),
        (Refrigerator.set_temp, 13, "Invalid temperature: 13"),
    ],
)
async def test_setters_invalid_arg(
    appliances_manager: AppliancesManager, method: Callable, argument: Any, message: str
):
    refrigerator = appliances_manager.refrigerators[0]
    with pytest.raises(ValueError) as exc_info:
        await getattr(refrigerator, method.__name__)(argument)

    assert message in str(exc_info.value)
