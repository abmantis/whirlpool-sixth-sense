from typing import cast

from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.dryer import (
    Cycle,
    Dryness,
    MachineState,
    Temperature,
    WrinkleShield,
)
from whirlpool.httpapi.dryer import Dryer


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


async def test_remote_control_enabled(appliances_manager: AppliancesManager):
    dryer = appliances_manager.dryers[0]
    assert dryer.get_remote_control_enabled() is False


async def test_model_specific_cycle_identity(appliances_manager: AppliancesManager):
    dryer = cast(Dryer, appliances_manager.dryers[0])

    assert dryer.get_dry_cycle_pair() is None
    assert dryer.get_utility_cycle() is None

    dryer.appliance_info.model_number = "WED9620HBK2"
    assert dryer.get_dry_cycle_pair() == ("regular", "timed_dry")
    assert dryer.get_utility_cycle() is None

    dryer.update_attributes({"DryCavity_CycleSetCycleSelect": 10}, 0)
    assert dryer.get_dry_cycle_pair() is None
    assert dryer.get_utility_cycle() == "steam_refresh"
