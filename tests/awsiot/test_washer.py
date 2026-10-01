"""Tests for the AWS IoT Washer class."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from whirlpool.awsiot.capabilities import parse_laundry_capability_profile
from whirlpool.awsiot.washer import Washer
from whirlpool.types import ApplianceInfo
from whirlpool.washer import MachineState

_DATA_DIR = Path(__file__).parent.parent / "data" / "awsiot"


def _load(name: str) -> dict[str, Any]:
    return json.loads((_DATA_DIR / name).read_text())


_STATE = _load("washer_state.json")
# A trimmed MFW7020RF0 capability file (W11812024): the file for this capture's
# own part (W11723751) is unpublished.
_CAPABILITY = _load("washer_capability.json")
# A Maytag MTW7205RR0 top-load washer in standby, with its own capability file
# (abmantis/whirlpool-sixth-sense#117).
_MTW7205RR0_STATE = _load("washer_MTW7205RR0_state.json")
_W11771387 = _load("capability_washer_W11771387.json")


def _make_washer(
    state: dict[str, Any] = _STATE,
    capability: dict[str, Any] = _CAPABILITY,
    model_number: str = "MFW7020RF0",
) -> Washer:
    mqtt = MagicMock()
    mqtt.client_id = "client"
    info = ApplianceInfo(
        said="WPR1W00000001",
        name="washer",
        category="laundry",
        model_number=model_number,
        serial_number="S",
    )
    profile = parse_laundry_capability_profile(capability, "washer")
    washer = Washer(mqtt, info, profile)
    washer.update_state(state)
    return washer


def test_machine_state_standby() -> None:
    assert _make_washer().get_machine_state() == MachineState.Standby


def test_door_closed() -> None:
    assert _make_washer().get_door_open() is False


def test_time_remaining() -> None:
    assert _make_washer().get_time_remaining() == 5351


def test_cycle_time_complete() -> None:
    assert _make_washer().get_cycle_time_complete() == 1783898525


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
        {"washer": {"applianceState": "running", "currentPhase": "wash"}}
    )
    assert washer.get_machine_state() == MachineState.RunningMainCycle
    assert washer.get_cycle_status_washing() is True
    # The other phases must remain false.
    assert washer.get_cycle_status_rinsing() is False


def test_end_state_maps_to_complete() -> None:
    washer = _make_washer()
    washer.update_state({"washer": {"applianceState": "end"}})
    assert washer.get_machine_state() == MachineState.Complete


# Every applianceState the washer map keeps. Standby is the #117 capture as-is;
# no washer capture holds the other four, so they are applied over it. Live
# reports: programming and end from an MFW7020RF0
# (https://github.com/abmantis/whirlpool-sixth-sense/pull/167#discussion_r3989687548,
# https://github.com/abmantis/whirlpool-sixth-sense/pull/167#discussion_r3989687563),
# running from an MTW7205RR0 getState reply (pickerin's TS_APPLIANCE_API.md).
# paused has only been captured on dryers, which share the message schema.
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(None, MachineState.Standby, id="standby"),
        pytest.param("programming", MachineState.Setting, id="programming"),
        pytest.param("running", MachineState.RunningMainCycle, id="running"),
        pytest.param("paused", MachineState.Pause, id="paused"),
        pytest.param("end", MachineState.Complete, id="end"),
    ],
)
def test_reported_appliance_state_maps(
    value: str | None, expected: MachineState
) -> None:
    washer = _make_washer(_MTW7205RR0_STATE, _W11771387, "MTW7205RR0")
    if value is not None:
        washer.update_state({"washer": {"applianceState": value}})
    assert washer.get_machine_state() == expected


# No AWS washer has reported these as applianceState. "idle" and "completed" are
# cycleTime.state values (the standby capture carries "idle"); the rest came
# from the HTTP backend's vocabulary.
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
    ],
)
def test_unconfirmed_appliance_state_is_unknown(value: str) -> None:
    washer = _make_washer(_MTW7205RR0_STATE, _W11771387, "MTW7205RR0")
    washer.update_state({"washer": {"applianceState": value}})
    assert washer.get_machine_state() is None
