"""Tests for the AWS IoT Dryer class."""

import json
from pathlib import Path
from unittest.mock import MagicMock

from whirlpool.awsiot.dryer import Dryer
from whirlpool.dryer import Dryness, MachineState, WrinkleShield
from whirlpool.types import ApplianceInfo

_STATE = json.loads(
    (Path(__file__).parent.parent / "data" / "awsiot" / "dryer_state.json").read_text()
)


def _make_dryer() -> Dryer:
    mqtt = MagicMock()
    mqtt.client_id = "client"
    info = ApplianceInfo(
        said="WPR1D00000002",
        name="dryer",
        category="laundry",
        model_number="MGD7020RF0",
        serial_number="S",
    )
    dryer = Dryer(mqtt, info)
    dryer.update_state(_STATE)
    return dryer


def test_machine_state_standby() -> None:
    assert _make_dryer().get_machine_state() == MachineState.Standby


def test_door_closed() -> None:
    assert _make_dryer().get_door_open() is False


def test_time_remaining() -> None:
    assert _make_dryer().get_time_remaining() == 2185


def test_cycle_time_complete() -> None:
    assert _make_dryer().get_cycle_time_complete() == 1783895096


def test_drum_light_off() -> None:
    assert _make_dryer().get_drum_light_on() is False


def test_cycle_status_flags_false_in_standby() -> None:
    dryer = _make_dryer()
    assert dryer.get_cycle_status_airflow_status() is False
    assert dryer.get_cycle_status_cool_down() is False
    assert dryer.get_cycle_status_damp() is False
    assert dryer.get_cycle_status_drying() is False
    assert dryer.get_cycle_status_limited_cycle() is False
    assert dryer.get_cycle_status_sensing() is False
    assert dryer.get_cycle_status_static_reduce() is False
    assert dryer.get_cycle_status_steaming() is False
    assert dryer.get_cycle_status_wet() is False


def test_wrinkle_shield_off() -> None:
    assert _make_dryer().get_wrinkle_shield() == WrinkleShield.Off


def test_dryness_decodes_known_level() -> None:
    assert _make_dryer().get_dryness() == Dryness.Normal


def test_running_cycle_reports_phase_and_state() -> None:
    dryer = _make_dryer()
    dryer.update_state(
        {"dryer": {"applianceState": "running", "currentPhase": "dry"}}
    )
    assert dryer.get_machine_state() == MachineState.RunningMainCycle
    assert dryer.get_cycle_status_drying() is True


def test_end_state_maps_to_complete() -> None:
    dryer = _make_dryer()
    dryer.update_state({"dryer": {"applianceState": "end"}})
    assert dryer.get_machine_state() == MachineState.Complete
