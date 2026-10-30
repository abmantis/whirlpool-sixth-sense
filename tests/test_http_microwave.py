import json
import logging
from collections.abc import Callable

import pytest
from aiointercept import aiointercept
from yarl import URL

from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.auth import Auth
from whirlpool.backendselector import BackendSelector
from whirlpool.httpapi.microwave import Microwave
from whirlpool.microwave import (
    HoodFanSpeed,
    MicrowaveCavityState,
    MicrowaveDoorStatus,
    Recipe,
)

from . import DATA_DIR


def _microwave(appliances_manager: AppliancesManager) -> Microwave:
    mwo = next(m for m in appliances_manager.microwaves if m.said == "SAIDMWO1")
    assert isinstance(mwo, Microwave)
    return mwo


async def test_mwo_data_model_is_a_microwave_not_an_oven(
    appliances_manager: AppliancesManager,
):
    assert "SAIDMWO1" in [m.said for m in appliances_manager.microwaves]
    assert "SAIDMWO1" not in [o.said for o in appliances_manager.ovens]


async def test_attributes(appliances_manager: AppliancesManager):
    mwo = _microwave(appliances_manager)
    assert mwo.get_online() is True
    assert mwo.get_cavity_state() == MicrowaveCavityState.Cooking
    assert mwo.get_door_status() == MicrowaveDoorStatus.Closed
    assert mwo.get_door_locked() is None
    assert mwo.get_cavity_light() is True
    assert mwo.get_display_temperature() == 65.0
    assert mwo.get_display_temperature_unit() == "C"
    assert mwo.get_turntable_enabled() is True
    assert mwo.get_mwo_power_level() is None
    assert mwo.get_cook_power_watts() == 750
    assert mwo.get_cook_timer_state() == "running"
    assert mwo.get_cook_timer_total_seconds() == 120
    assert mwo.get_cook_time_remaining() == 90
    assert mwo.get_cook_time_elapsed() == 30
    assert mwo.get_cycle_count() == 31
    assert mwo.get_control_locked() is False
    assert mwo.get_sabbath_mode() is False
    assert mwo.get_kitchen_timer().get_remaining_time() == 0
    assert mwo.get_active_recipe_id() is None
    assert mwo.get_hood_fan_speed() is None
    assert mwo.supports_control_lock() is True
    assert mwo.supports_sabbath_mode() is True
    assert mwo.supports_hood_fan() is False
    assert mwo.supports_hood_light_level() is False
    assert mwo.supports_hood_light_color() is False
    assert mwo.supports_quiet_mode() is False


@pytest.mark.parametrize(
    ["method", "arguments", "expected_json"],
    [
        (Microwave.set_cavity_light, {"on": False}, {"Mwo_DisplaySetLightOn": "0"}),
        (Microwave.stop_cook, {}, {"Mwo_OperationSetOperations": "1"}),
        (
            Microwave.set_control_locked,
            {"on": True},
            {"Sys_OperationSetControlLock": "1"},
        ),
        (
            Microwave.set_sabbath_mode,
            {"on": True},
            {"Sys_OperationSetSabbathModeEnabled": "1"},
        ),
    ],
)
async def test_setters(
    appliances_manager: AppliancesManager,
    auth: Auth,
    backend_selector: BackendSelector,
    aiointercept_mock: aiointercept,
    method: Callable,
    arguments: dict,
    expected_json: dict,
):
    mwo = _microwave(appliances_manager)
    expected_payload = {
        "json": {
            "body": expected_json,
            "header": {"said": mwo.said, "command": "setAttributes"},
        }
    }
    url = backend_selector.appliance_command_url

    aiointercept_mock.post(url, payload=expected_payload)
    assert await getattr(mwo, method.__name__)(**arguments)

    aiointercept_mock.assert_called_with(
        url=url,
        method="POST",
        data=None,
        json=expected_payload["json"],
        headers=auth.create_headers(),
    )
    assert len(aiointercept_mock.requests[("POST", URL(url))]) == 1


async def test_unsupported_setters_send_nothing(
    appliances_manager: AppliancesManager,
    backend_selector: BackendSelector,
    aiointercept_mock: aiointercept,
):
    mwo = _microwave(appliances_manager)
    assert await mwo.set_cook(Recipe.Microwave, 60, power_level=50) is False
    assert await mwo.set_hood_fan_speed(HoodFanSpeed.Low) is False
    assert await mwo.set_quiet_mode(True) is False
    url = backend_selector.appliance_command_url
    assert ("POST", URL(url)) not in aiointercept_mock.requests


@pytest.mark.parametrize(
    ["state_raw", "expected"],
    [
        ("0", MicrowaveCavityState.Idle),
        ("2", MicrowaveCavityState.Idle),
        ("4", MicrowaveCavityState.Cooking),
        ("7", MicrowaveCavityState.Paused),
        ("13", MicrowaveCavityState.Completed),
        ("9", None),
    ],
)
async def test_cavity_state_values(
    appliances_manager: AppliancesManager,
    backend_selector: BackendSelector,
    aiointercept_mock: aiointercept,
    caplog: pytest.LogCaptureFixture,
    state_raw: str,
    expected: MicrowaveCavityState | None,
):
    mwo = _microwave(appliances_manager)
    with open(DATA_DIR / "mock_data.json") as f:
        payload = json.load(f)[mwo.said]
    payload["attributes"]["Mwo_OperationStatusState"]["value"] = state_raw

    aiointercept_mock.get(
        backend_selector.get_appliance_data_url(mwo.said), payload=payload
    )
    assert await mwo.fetch_data()

    caplog.set_level(logging.ERROR)
    caplog.clear()
    assert mwo.get_cavity_state() == expected
    assert not caplog.records
