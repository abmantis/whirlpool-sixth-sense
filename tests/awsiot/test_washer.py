"""Tests for the AWS IoT Washer class."""

import json
import time
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


# MFW7020RF0 front-load, with a trimmed W11812024 file.
_STATE = _load("washer_state.json")
_CAPABILITY = _load("washer_capability.json")
# MTW7205RR0 top-load in standby, with its W11771387 file.
_MTW7205RR0_STATE = _load("washer_MTW7205RR0_state.json")
_W11771387 = _load("capability_washer_W11771387.json")
# WFW5720RR0 front-load in standby, with its W11738987 file.
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
    assert washer.get_cycle_status_rinsing() is False


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
    assert _phase_flags(_running_front_load(phase)) == {
        name: name == flag for name in _FLAGS
    }


@pytest.mark.parametrize(
    "phase", ["addGarment", "preWash", "preSense", "intermediateSpin", "default"]
)
def test_unmapped_phase_sets_no_flag(phase: str) -> None:
    assert _phase_flags(_running_front_load(phase)) == dict.fromkeys(_FLAGS, False)


def test_phase_flags_are_unknown_without_a_phase() -> None:
    washer = _make_washer(
        {"washer": {"applianceState": "running"}}, _W11738987, "WFW5720RR0"
    )
    assert _phase_flags(washer) == {
        name: False if name == "soaking" else None for name in _FLAGS
    }


def test_empty_phase_sets_no_flag() -> None:
    washer = _make_washer(_WFW5720RR0_STATE, _W11738987, "WFW5720RR0")
    assert _phase_flags(washer) == dict.fromkeys(_FLAGS, False)


# A getState reply from a running MTW7205RR0 top-load.
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
_MTW7205RR0_PREDICTED_END = 1775397826


def _running_top_load() -> Washer:
    washer = _make_washer(_MTW7205RR0_STATE, _W11771387, "MTW7205RR0")
    washer.update_state(_MTW7205RR0_RUNNING_RINSE)
    return washer


def test_top_load_reports_rinsing() -> None:
    washer = _running_top_load()
    assert washer.get_machine_state() == MachineState.RunningMainCycle
    assert _phase_flags(washer) == {name: name == "rinsing" for name in _FLAGS}


def _freeze_clock(monkeypatch: pytest.MonkeyPatch, now: int) -> None:
    monkeypatch.setattr(time, "time", lambda: float(now))


def test_time_remaining_counts_down_to_the_predicted_end(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _freeze_clock(monkeypatch, _MTW7205RR0_PREDICTED_END - 600)
    washer = _running_top_load()
    assert washer.get_time_remaining() == 600
    assert washer.get_cycle_time_complete() == _MTW7205RR0_PREDICTED_END


def test_time_remaining_stops_at_zero_past_the_predicted_end(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _freeze_clock(monkeypatch, _MTW7205RR0_PREDICTED_END + 60)
    washer = _running_top_load()
    assert washer.get_time_remaining() == 0
    assert washer.get_cycle_time_complete() == _MTW7205RR0_PREDICTED_END


def test_time_is_unknown_while_paused(monkeypatch: pytest.MonkeyPatch) -> None:
    _freeze_clock(monkeypatch, _MTW7205RR0_PREDICTED_END - 600)
    washer = _running_top_load()
    washer.update_state(
        {"washer": {"applianceState": "paused", "cycleTime": {"state": "paused"}}}
    )
    assert washer.get_time_remaining() is None
    assert washer.get_cycle_time_complete() is None


def test_time_is_unknown_while_the_cycle_time_is_not_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _freeze_clock(
        monkeypatch, _MTW7205RR0_STATE["washer"]["cycleTime"]["timeComplete"] - 600
    )
    washer = _make_washer(_MTW7205RR0_STATE, _W11771387, "MTW7205RR0")
    washer.update_state({"washer": {"applianceState": "running"}})
    assert washer.get_machine_state() == MachineState.RunningMainCycle
    assert washer.get_time_remaining() is None
    assert washer.get_cycle_time_complete() is None


@pytest.mark.parametrize(
    ("state", "capability", "model"),
    [
        pytest.param(_MTW7205RR0_STATE, _W11771387, "MTW7205RR0", id="MTW7205RR0"),
        pytest.param(_WFW5720RR0_STATE, _W11738987, "WFW5720RR0", id="WFW5720RR0"),
    ],
)
def test_time_is_unknown_outside_a_running_cycle(
    monkeypatch: pytest.MonkeyPatch,
    state: dict[str, Any],
    capability: dict[str, Any],
    model: str,
) -> None:
    _freeze_clock(monkeypatch, state["washer"]["cycleTime"]["timeComplete"] - 600)
    washer = _make_washer(state, capability, model)
    assert washer.get_time_remaining() is None
    assert washer.get_cycle_time_complete() is None


_DISPENSER_CASES = [
    pytest.param(_WFW5720RR0_STATE, _W11738987, "WFW5720RR0", id="WFW5720RR0"),
    pytest.param(_MTW7205RR0_STATE, _W11771387, "MTW7205RR0", id="MTW7205RR0"),
]


@pytest.mark.parametrize(("state", "capability", "model"), _DISPENSER_CASES)
def test_dispense_level_is_not_supported(
    state: dict[str, Any], capability: dict[str, Any], model: str
) -> None:
    assert _make_washer(state, capability, model).supports_dispense_level() is False


@pytest.mark.parametrize(("state", "capability", "model"), _DISPENSER_CASES)
def test_dispense_level_raises(
    state: dict[str, Any], capability: dict[str, Any], model: str
) -> None:
    with pytest.raises(NotImplementedError):
        _make_washer(state, capability, model).get_dispense_1_level()


# An MTW7205RF1 top-load through one regularNormal cycle: each file is the
# state update_state held at that moment.
def _mtw7205rf1_state(moment: str) -> dict[str, Any]:
    return _load(f"washer_MTW7205RF1_{moment}.json")


def _mtw7205rf1(moment: str) -> Washer:
    return _make_washer(_mtw7205rf1_state(moment), _W11771387, "MTW7205RF1")


@pytest.mark.parametrize(
    ("moment", "expected"),
    [
        ("programming", MachineState.Setting),
        ("sensing", MachineState.RunningMainCycle),
        ("paused", MachineState.Pause),
        ("end", MachineState.Complete),
    ],
)
def test_live_cycle_state_maps(moment: str, expected: MachineState) -> None:
    assert _mtw7205rf1(moment).get_machine_state() == expected


@pytest.mark.parametrize("phase", ["sensing", "filling", "washing"])
def test_live_top_load_phase_sets_only_its_flag(phase: str) -> None:
    assert _mtw7205rf1_state(phase)["washer"]["currentPhase"] == phase
    assert _phase_flags(_mtw7205rf1(phase)) == {name: name == phase for name in _FLAGS}


@pytest.mark.parametrize(("moment", "phase"), [("prewash", "preWash"), ("end", "done")])
def test_live_phase_without_a_flag_sets_none(moment: str, phase: str) -> None:
    assert _mtw7205rf1_state(moment)["washer"]["currentPhase"] == phase
    assert _phase_flags(_mtw7205rf1(moment)) == dict.fromkeys(_FLAGS, False)


def test_live_time_remaining_counts_down_while_the_cycle_time_runs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _mtw7205rf1_state("filling")
    predicted_end = state["washer"]["cycleTime"]["timeComplete"]
    _freeze_clock(monkeypatch, predicted_end - 600)
    washer = _mtw7205rf1("filling")
    assert washer.get_time_remaining() == 600
    assert washer.get_cycle_time_complete() == predicted_end


def test_live_time_is_unknown_while_the_cycle_time_holds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # cycleTime.state "paused" under a running applianceState, during a fill.
    state = _mtw7205rf1_state("cycle_time_paused")
    assert state["washer"]["cycleTime"]["state"] == "paused"
    _freeze_clock(monkeypatch, state["washer"]["cycleTime"]["timeComplete"] - 600)
    washer = _mtw7205rf1("cycle_time_paused")
    assert washer.get_machine_state() == MachineState.RunningMainCycle
    assert washer.get_time_remaining() is None
    assert washer.get_cycle_time_complete() is None


# doorStatus is the lid; doorLockStatus is a separate lock.
@pytest.mark.parametrize(
    ("moment", "door_open"),
    [("paused", True), ("programming", False), ("filling", False)],
)
def test_live_door_follows_the_lid(moment: str, door_open: bool) -> None:
    assert _mtw7205rf1(moment).get_door_open() is door_open
