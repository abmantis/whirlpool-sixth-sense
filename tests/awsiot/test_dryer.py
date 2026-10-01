"""Tests for the AWS IoT Dryer class."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from whirlpool.awsiot.capabilities import parse_laundry_capability_profile
from whirlpool.awsiot.dryer import Dryer
from whirlpool.dryer import Dryness, MachineState, WrinkleShield
from whirlpool.types import ApplianceInfo

_DATA_DIR = Path(__file__).parent.parent / "data" / "awsiot"


def _load(name: str) -> dict[str, Any]:
    return json.loads((_DATA_DIR / name).read_text())


_STATE = _load("dryer_state.json")
# A trimmed MGD7020RF0 capability file (W11804872): the file for this capture's
# own part (W11729930) is unpublished.
_CAPABILITY = _load("dryer_capability.json")
# The MGD7205RR0 (#117) and MED7205RW0 (home-assistant/core#151547) dryers both
# declare part W11771436, and both owners posted this same file with their states.
_W11771436 = _load("capability_dryer_W11771436.json")


def _make_dryer(
    state: dict[str, Any] = _STATE,
    capability: dict[str, Any] = _CAPABILITY,
    model_number: str = "MGD7020RF0",
) -> Dryer:
    mqtt = MagicMock()
    mqtt.client_id = "client"
    info = ApplianceInfo(
        said="WPR1D00000002",
        name="dryer",
        category="laundry",
        model_number=model_number,
        serial_number="S",
    )
    profile = parse_laundry_capability_profile(capability, "dryer")
    dryer = Dryer(mqtt, info, profile)
    dryer.update_state(state)
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
    dryer.update_state({"dryer": {"applianceState": "running", "currentPhase": "dry"}})
    assert dryer.get_machine_state() == MachineState.RunningMainCycle
    assert dryer.get_cycle_status_drying() is True


def test_end_state_maps_to_complete() -> None:
    dryer = _make_dryer()
    dryer.update_state({"dryer": {"applianceState": "end"}})
    assert dryer.get_machine_state() == MachineState.Complete


# Every applianceState the dryer map keeps, each read from a real capture. The
# MED7205RW0 snapshots are Lifedelinquent's, taken over one timed40 cycle.
@pytest.mark.parametrize(
    ("model_number", "state_file", "expected"),
    [
        pytest.param(
            "MGD7205RR0",
            "dryer_MGD7205RR0_state.json",
            MachineState.Standby,
            id="standby",
        ),
        pytest.param(
            "MED7205RW0",
            "dryer_MED7205RW0_programming.json",
            MachineState.Setting,
            id="programming",
        ),
        pytest.param(
            "MED7205RW0",
            "dryer_MED7205RW0_running.json",
            MachineState.RunningMainCycle,
            id="running",
        ),
        pytest.param(
            "MED7205RW0",
            "dryer_MED7205RW0_paused.json",
            MachineState.Pause,
            id="paused",
        ),
        pytest.param(
            "MED7205RW0",
            "dryer_MED7205RW0_end.json",
            MachineState.Complete,
            id="end",
        ),
    ],
)
def test_captured_appliance_state_maps(
    model_number: str, state_file: str, expected: MachineState
) -> None:
    dryer = _make_dryer(_load(state_file), _W11771436, model_number)
    assert dryer.get_machine_state() == expected


# No AWS dryer has reported these as applianceState. "idle" and "completed" are
# cycleTime.state values (the standby and end snapshots above carry them); the
# rest came from the HTTP backend's vocabulary.
@pytest.mark.parametrize(
    "value",
    [
        "idle",
        "completed",
        "setting",
        "delayCountdown",
        "delayPaused",
        "pause",
        "postCycle",
        "complete",
        "exception",
        "exceptions",
        "powerFailure",
        "cancelled",
    ],
)
def test_unconfirmed_appliance_state_is_unknown(value: str) -> None:
    dryer = _make_dryer(_load("dryer_MGD7205RR0_state.json"), _W11771436, "MGD7205RR0")
    dryer.update_state({"dryer": {"applianceState": value}})
    assert dryer.get_machine_state() is None
