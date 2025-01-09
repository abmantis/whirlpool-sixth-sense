import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from yarl import URL

from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.backendselector import BackendSelector
from whirlpool.dryer import Dryer, MachineState

ACCOUNT_ID = 111222333


CURR_DIR = Path(__file__).parent
DATA_DIR = CURR_DIR / "data"

DRYER_DATA = json.loads((DATA_DIR / "dryer_data.json").read_text())

DATA1 = DRYER_DATA["DATA1"]


async def test_attributes(
    dryer: Dryer, backend_selector_mock: BackendSelector, aioresponses_mock, appliances_manager
):
    aioresponses_mock.get(
        backend_selector_mock.ws_url,
        payload={"url": "wss://something"},
        repeat=True,
    )
    aioresponses_mock.get(
        backend_selector_mock.get_appliance_data_url(dryer.said), payload=DATA1
    )

    await dryer.fetch_data()

    await appliances_manager.connect()
    assert dryer.get_machine_state() == MachineState.Standby
    assert dryer.get_machine_state_value() == 0
    assert dryer.get_op_status_dooropen() == False
    assert dryer.get_time_status_est_time_remaining() == 1800
    assert dryer.get_drum_light_on() == 0
    assert dryer.get_change_status_steamchangeable() == 1
    assert dryer.get_change_status_cycleselect() == 0
    assert dryer.get_change_status_dryness() == 1
    assert dryer.get_change_status_manualdrytime() == 1
    assert dryer.get_change_status_temperature() == 1
    assert dryer.get_change_status_wrinkleshield() == 1
    assert dryer.get_dryness() == 10
    assert dryer.get_manual_dry_time() == 1800
    assert dryer.get_cycle_select() == 11
    assert dryer.get_cycle_status_airflow_status() == 0
    assert dryer.get_cycle_status_cool_down() == 0
    assert dryer.get_cycle_status_damp() == 0
    assert dryer.get_cycle_status_drying() == 0
    assert dryer.get_cycle_status_limited_cycle() == 0
    assert dryer.get_cycle_status_sensing() == 0
    assert dryer.get_cycle_status_static_reduce() == 0
    assert dryer.get_cycle_status_steaming() == 0
    assert dryer.get_cycle_status_wet() == 0
    assert dryer.get_odometer_status_cycle_count() == 195
    assert dryer.get_odometer_status_running_hours() == 148
    assert dryer.get_odometer_status_total_hours() == 6302
    assert dryer.get_wifi_status_rssi_antenna_diversity() == -51
    assert dryer.get_damp_notification_tone_volume() == 0
    assert dryer.get_alert_tone_volume() == 0
    assert dryer.get_temperature() == 2
    assert dryer.get_wrinkle_shield() == 0
    await appliances_manager.disconnect()

