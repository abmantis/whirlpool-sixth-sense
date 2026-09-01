"""Tests for the AWS IoT Washer class."""

import json
from pathlib import Path
from unittest.mock import MagicMock

from whirlpool.awsiot.washer import Washer
from whirlpool.types import ApplianceInfo
from whirlpool.washer import MachineState

_STATE = json.loads(
    (Path(__file__).parent.parent / "data" / "awsiot" / "washer_state.json").read_text()
)


def _make_washer() -> Washer:
    mqtt = MagicMock()
    mqtt.client_id = "client"
    info = ApplianceInfo(
        said="WPR1W00000001",
        name="washer",
        category="laundry",
        model_number="MFW7020RF0",
        serial_number="S",
    )
    washer = Washer(mqtt, info)
    washer.update_state(_STATE)
    return washer


def test_machine_state_standby() -> None:
    assert _make_washer().get_machine_state() == MachineState.Standby


def test_door_closed() -> None:
    assert _make_washer().get_door_open() is False


def test_time_remaining() -> None:
    assert _make_washer().get_time_remaining() == 5351


def test_cycle_status_flags_false_in_standby() -> None:
    washer = _make_washer()
    assert washer.get_cycle_status_sensing() is False
    assert washer.get_cycle_status_filling() is False
    assert washer.get_cycle_status_soaking() is False
    assert washer.get_cycle_status_washing() is False
    assert washer.get_cycle_status_rinsing() is False
    assert washer.get_cycle_status_spinning() is False


def test_running_cycle_reports_phase_and_state() -> None:
    washer = _make_washer()
    washer.update_state(
        {"washer": {"applianceState": "running", "currentPhase": "washing"}}
    )
    assert washer.get_machine_state() == MachineState.RunningMainCycle
    assert washer.get_cycle_status_washing() is True
    # The other phases must remain false.
    assert washer.get_cycle_status_rinsing() is False
