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
# A Whirlpool WFW5720RR0 front-load washer in standby, with its own capability
# file (abmantis/whirlpool-sixth-sense#179). The state reports
# capabilityPartNumber "P0139460020" while the file declares "W11738987", as
# captured.
_WFW5720RR0_STATE = _load("washer_WFW5720RR0_state.json")
_W11738987 = _load("capability_washer_W11738987.json")


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


_FLAGS = ("sensing", "filling", "soaking", "washing", "rinsing", "spinning")


def _phase_flags(washer: Washer) -> dict[str, bool | None]:
    return {
        "sensing": washer.get_cycle_status_sensing(),
        "filling": washer.get_cycle_status_filling(),
        "soaking": washer.get_cycle_status_soaking(),
        "washing": washer.get_cycle_status_washing(),
        "rinsing": washer.get_cycle_status_rinsing(),
        "spinning": washer.get_cycle_status_spinning(),
    }


def _running_front_load(phase: str) -> Washer:
    washer = _make_washer(_WFW5720RR0_STATE, _W11738987, "WFW5720RR0")
    washer.update_state(
        {"washer": {"applianceState": "running", "currentPhase": phase}}
    )
    return washer


# Every currentPhase spelling the washer maps. Front-loads report the stem: an
# MFW7020RF0 quick wash went sense, addGarment, wash, rinse, extraRinse, rinse,
# spin (https://github.com/abmantis/whirlpool-sixth-sense/pull/167#discussion_r3989687563).
# The top-load W11771387 file enumerates the gerunds sensing, filling and
# washing instead.
@pytest.mark.parametrize(
    ("phase", "flag"),
    [
        ("sense", "sensing"),
        ("sensing", "sensing"),
        ("fill", "filling"),
        ("filling", "filling"),
        ("wash", "washing"),
        ("washing", "washing"),
        ("rinse", "rinsing"),
        ("extraRinse", "rinsing"),
        ("spin", "spinning"),
    ],
)
def test_mapped_phase_sets_only_its_flag(phase: str, flag: str) -> None:
    # Home Assistant shows the first flag that is True, so a spelling under two
    # flags would show the wrong phase.
    assert _phase_flags(_running_front_load(phase)) == {
        name: name == flag for name in _FLAGS
    }


# Phases a capability file enumerates but nothing maps: addGarment and default
# have no flag; preSense, intermediateSpin and preWash were never reported live,
# and preWash could mean soaking or washing.
@pytest.mark.parametrize(
    "phase", ["addGarment", "preWash", "preSense", "intermediateSpin", "default"]
)
def test_unmapped_phase_sets_no_flag(phase: str) -> None:
    assert _phase_flags(_running_front_load(phase)) == dict.fromkeys(_FLAGS, False)


def test_phase_flags_are_unknown_without_a_phase() -> None:
    # A fresh washer whose state has no currentPhase key at all; merging a delta
    # over a capture would keep the capture's "".
    washer = _make_washer(
        {"washer": {"applianceState": "running"}}, _W11738987, "WFW5720RR0"
    )
    assert _phase_flags(washer) == dict.fromkeys(_FLAGS, None)


def test_empty_phase_sets_no_flag() -> None:
    # The standby capture reports currentPhase "".
    washer = _make_washer(_WFW5720RR0_STATE, _W11738987, "WFW5720RR0")
    assert _phase_flags(washer) == dict.fromkeys(_FLAGS, False)


def test_soaking_is_false_during_prewash() -> None:
    # Home Assistant reads all six flags on every update while the washer runs,
    # so soaking must answer rather than raise. No reported or enumerated phase
    # is known to mean soaking.
    assert _running_front_load("preWash").get_cycle_status_soaking() is False


# A getState reply from a running MTW7205RR0 top-load, as published in
# https://github.com/pickerin/maytag_laundry_homeassistant/blob/5ea31accfd67ff21aaf8b132b6efd4bd2f913c30/TS_APPLIANCE_API.md#L206-L240
_MTW7205RR0_RUNNING_RINSE: dict[str, Any] = {
    "washer": {
        "applianceState": "running",
        "cycleName": "cleanWasher",
        "cycleType": "standard",
        "specialName": "",
        "currentPhase": "rinse",
        "cycleTime": {
            "state": "running",
            "time": 3665,
            "timeComplete": 1775397826,
            "timePaused": 1775394975,
        },
        "delayTime": {
            "state": "idle",
            "time": 0,
            "timeComplete": 0,
            "timePaused": 0,
        },
        "sessionId": "50fb9c3e-8231-4edf-92ce-69fb893558b5",
        "cleanWasher": False,
        "doorStatus": "closed",
        "doorLockStatus": True,
    },
    "remoteStartEnable": False,
    "faultHistory": ["F0E3", "F8E6", "F0E5", "none", "none"],
    "activeFault": "none",
    "faucet": {
        "faucetState": "FAUCET_IDLE",
        "soakDuration": {"timeComplete": 1775396458},
    },
    "sound": {"cycleSignal": "max"},
    "capabilityPartNumber": "W11771387",
    "systemVersion": "0.0.0",
}


def test_top_load_reports_rinsing() -> None:
    washer = _make_washer(_MTW7205RR0_STATE, _W11771387, "MTW7205RR0")
    washer.update_state(_MTW7205RR0_RUNNING_RINSE)
    assert washer.get_machine_state() == MachineState.RunningMainCycle
    assert _phase_flags(washer) == {name: name == "rinsing" for name in _FLAGS}
