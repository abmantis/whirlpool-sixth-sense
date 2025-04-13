from collections.abc import Callable
from typing import Any

import pytest
from aioresponses import aioresponses
from yarl import URL

from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.auth import Auth
from whirlpool.backendselector import BackendSelector
from whirlpool.dryer import MachineState


async def test_attributes(appliances_manager: AppliancesManager):
    dryer1 = appliances_manager.dryers[0]
    assert dryer1.get_machine_state() == MachineState.Standby
    assert dryer1.get_door_open() is False
    assert dryer1.get_est_time_remaining() == 1800
    assert dryer1.get_drum_light_on() == 0
    assert dryer1.get_status_extra_steam_changeable() == 1
    assert dryer1.get_status_cycle_select() == 0
    assert dryer1.get_status_dryness() == 1
    assert dryer1.get_status_manual_dry_time() == 1
    assert dryer1.get_status_temperature() == 1
    assert dryer1.get_status_wrinkle_shield() == 1
    assert dryer1.get_dryness() == 10
    assert dryer1.get_manual_dry_time() == 1800
    assert dryer1.get_cycle_select() == 11
    assert dryer1.get_airflow_status() == 0
    assert dryer1.get_cool_down() == 0
    assert dryer1.get_damp() == 0
    assert dryer1.get_drying() == 0
    assert dryer1.get_limited_cycle() == 0
    assert dryer1.get_sensing() == 0
    assert dryer1.get_static_reduce() == 0
    assert dryer1.get_steaming() == 0
    assert dryer1.get_wet() == 0
    assert dryer1.get_cycle_count() == 195
    assert dryer1.get_running_hours() == 148
    assert dryer1.get_total_hours() == 6302
    assert dryer1.get_rssi_antenna_diversity() == -51
    assert dryer1.get_damp_notification_tone_volume() == 0
    assert dryer1.get_alert_tone_volume() == 0
    assert dryer1.get_temperature() == 2
    assert dryer1.get_wrinkle_shield() == 0


@pytest.mark.parametrize(
    ["method", "argument", "expected_json"],
    [
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
    dryer = appliances_manager.dryers[0]

    expected_payload = {
        "json": {
            "body": expected_json,
            "header": {"said": dryer.said, "command": "setAttributes"},
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
    await method(dryer, argument)

    # assert args and length
    aioresponses_mock.assert_called_with(**post_request_call_kwargs)
    assert len(aioresponses_mock.requests[("POST", URL(url))]) == 1
