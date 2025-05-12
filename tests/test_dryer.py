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
    assert not dryer.get_door_open()
    assert dryer.get_est_time_remaining() == 1800
    assert not dryer.get_drum_light_on()
    assert dryer.get_status_extra_steam_changeable()
    assert not dryer.get_status_cycle_select()
    assert dryer.get_status_dryness()
    assert dryer.get_status_manual_dry_time()
    assert dryer.get_status_temperature()
    assert dryer.get_status_wrinkle_shield()
    assert dryer.get_dryness() == Dryness.High
    assert dryer.get_manual_dry_time() == 1800
    assert dryer.get_cycle_select() == CycleSelect.Timed_Dry
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


