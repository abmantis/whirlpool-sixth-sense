from yarl import URL
from aiointercept import aiointercept
import pytest

from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.auth import Auth
from whirlpool.backendselector import BackendSelector
from whirlpool.dryer import (
    Cycle,
    Dryness,
    MachineState,
    Temperature,
    WrinkleShield,
)



async def test_attributes(appliances_manager: AppliancesManager):
    dryer = appliances_manager.dryers[0]
    assert dryer.get_machine_state() == MachineState.Standby
    assert not dryer.get_door_open()
    assert dryer.get_time_remaining() == 1800
    assert not dryer.get_drum_light_on()
    assert dryer.get_steam_changeable()
    assert not dryer.get_cycle_changeable()
    assert dryer.get_dryness_changeable()
    assert dryer.get_manual_dry_time_changeable()
    assert dryer.get_steam_changeable()
    assert dryer.get_wrinkle_shield_changeable()
    assert dryer.get_dryness() == Dryness.High
    assert dryer.get_manual_dry_time() == 1800
    assert dryer.get_cycle() == Cycle.TimedDry
    assert not dryer.get_cycle_status_airflow_status()
    assert not dryer.get_cycle_status_cool_down()
    assert not dryer.get_cycle_status_damp()
    assert not dryer.get_cycle_status_drying()
    assert not dryer.get_cycle_status_limited_cycle()
    assert not dryer.get_cycle_status_sensing()
    assert not dryer.get_cycle_status_static_reduce()
    assert not dryer.get_cycle_status_steaming()
    assert not dryer.get_cycle_status_wet()
    assert dryer.get_cycle_count() == 195
    assert dryer.get_damp_notification_tone_volume() == 0
    assert dryer.get_alert_tone_volume() == 0
    assert dryer.get_temperature() == Temperature.Cool
    assert dryer.get_wrinkle_shield() == WrinkleShield.Off


@pytest.mark.parametrize(
    ("method_name", "operation"),
    (("start", "2"), ("pause", "5"), ("resume", "6"), ("cancel", "1")),
)
async def test_command_setters(
    appliances_manager: AppliancesManager,
    auth: Auth,
    backend_selector: BackendSelector,
    aiointercept_mock: aiointercept,
    method_name: str,
    operation: str,
):
    dryer = appliances_manager.dryers[0]
    url = backend_selector.appliance_command_url
    expected_json = {
        "body": {"Cavity_OpSetOperations": operation},
        "header": {"said": dryer.said, "command": "setAttributes"},
    }
    aiointercept_mock.post(url, payload=expected_json)

    assert await getattr(dryer, method_name)()

    aiointercept_mock.assert_called_with(
        url=url,
        method="POST",
        data=None,
        json=expected_json,
        headers=auth.create_headers(),
    )
    assert len(aiointercept_mock.requests[("POST", URL(url))]) == 1


async def test_remote_control_enabled(appliances_manager: AppliancesManager):
    dryer = appliances_manager.dryers[0]
    assert dryer.get_remote_control_enabled() is False
