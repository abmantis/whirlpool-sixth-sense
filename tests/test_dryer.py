from collections.abc import Callable
from typing import Any

import pytest
from aioresponses import aioresponses
from yarl import URL

from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.auth import Auth
from whirlpool.backendselector import BackendSelector
from whirlpool.dryer import (
    CycleSelect,
    Dryness,
    MachineState,
    Temperature,
    WrinkleShield,
)


async def test_attributes(appliances_manager: AppliancesManager):
    dryer = appliances_manager.dryers[0]
    assert dryer.get_machine_state() == MachineState.Standby
    assert dryer.get_door_open() is False
    assert dryer.get_est_time_remaining() == 1800
    assert dryer.get_drum_light_on() == 0
    assert dryer.get_status_extra_steam_changeable() == 1
    assert dryer.get_status_cycle_select() == 0
    assert dryer.get_status_dryness() == 1
    assert dryer.get_status_manual_dry_time() == 1
    assert dryer.get_status_temperature() == 1
    assert dryer.get_status_wrinkle_shield() == 1
    assert dryer.get_dryness() == Dryness.High
    assert dryer.get_manual_dry_time() == 1800
    assert dryer.get_cycle_select() == CycleSelect.Timed_Dry
    assert dryer.get_cycle_status_airflow_status() == 0
    assert dryer.get_cycle_status_cool_down() == 0
    assert dryer.get_cycle_status_damp() == 0
    assert dryer.get_cycle_status_drying() == 0
    assert dryer.get_cycle_status_limited_cycle() == 0
    assert dryer.get_cycle_status_sensing() == 0
    assert dryer.get_cycle_status_static_reduce() == 0
    assert dryer.get_cycle_status_steaming() == 0
    assert dryer.get_cycle_status_wet() == 0
    assert dryer.get_cycle_count() == 195
    assert dryer.get_running_hours() == 148
    assert dryer.get_total_hours() == 6302
    assert dryer.get_rssi_antenna_diversity() == -51
    assert dryer.get_damp_notification_tone_volume() == 0
    assert dryer.get_alert_tone_volume() == 0
    assert dryer.get_temperature() == Temperature.Cool
    assert dryer.get_wrinkle_shield() == WrinkleShield.Off


