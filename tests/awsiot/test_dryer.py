"""Tests for the AWS IoT Dryer class."""

import copy
import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from whirlpool.awsiot.capabilities import parse_laundry_capability_profile
from whirlpool.awsiot.dryer import Dryer
from whirlpool.dryer import Cycle, MachineState, Temperature, WrinkleShield
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


def test_drum_light_off() -> None:
    assert _make_dryer().get_drum_light_on() is False


def test_wrinkle_shield_off() -> None:
    assert _make_dryer().get_wrinkle_shield() == WrinkleShield.Off


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


_FLAGS = ("cool_down", "drying", "sensing", "static_reduce", "steaming")


def _phase_flags(dryer: Dryer) -> dict[str, bool | None]:
    return {
        "cool_down": dryer.get_cycle_status_cool_down(),
        "drying": dryer.get_cycle_status_drying(),
        "sensing": dryer.get_cycle_status_sensing(),
        "static_reduce": dryer.get_cycle_status_static_reduce(),
        "steaming": dryer.get_cycle_status_steaming(),
    }


_MED7205RW0_RUNNING = "dryer_MED7205RW0_running.json"


def _med7205rw0(state_file: str = _MED7205RW0_RUNNING) -> Dryer:
    return _make_dryer(_load(state_file), _W11771436, "MED7205RW0")


def _running_med7205rw0(phase: str) -> Dryer:
    dryer = _med7205rw0()
    dryer.update_state({"dryer": {"currentPhase": phase}})
    return dryer


# Every currentPhase spelling the dryer maps. The MED7205RW0 timed40 cycle
# reported dry while running and coolDown from there to the end (phase None:
# read as captured); sensing, steaming and staticReduce are the flags' own
# words, enumerated in W11771436.
@pytest.mark.parametrize(
    ("state_file", "phase", "flag"),
    [
        pytest.param(_MED7205RW0_RUNNING, None, "drying", id="dry"),
        pytest.param("dryer_MED7205RW0_end.json", None, "cool_down", id="coolDown"),
        pytest.param(_MED7205RW0_RUNNING, "sensing", "sensing", id="sensing"),
        pytest.param(_MED7205RW0_RUNNING, "steaming", "steaming", id="steaming"),
        pytest.param(
            _MED7205RW0_RUNNING, "staticReduce", "static_reduce", id="staticReduce"
        ),
    ],
)
def test_mapped_phase_sets_only_its_flag(
    state_file: str, phase: str | None, flag: str
) -> None:
    dryer = _med7205rw0(state_file)
    if phase is not None:
        dryer.update_state({"dryer": {"currentPhase": phase}})
    assert _phase_flags(dryer) == {name: name == flag for name in _FLAGS}


def test_pets_care_sets_no_flag() -> None:
    # W11771436 lists petsCare beside sensing, but no dryer has reported it and
    # nothing says what it is.
    assert _phase_flags(_running_med7205rw0("petsCare")) == dict.fromkeys(_FLAGS, False)


def test_phase_flags_are_unknown_without_a_phase() -> None:
    # A fresh dryer whose state has no currentPhase key at all; merging a delta
    # over a capture would keep the capture's phase.
    dryer = _make_dryer(
        {"dryer": {"applianceState": "running"}}, _W11771436, "MED7205RW0"
    )
    assert _phase_flags(dryer) == dict.fromkeys(_FLAGS, None)


def test_empty_phase_sets_no_flag() -> None:
    # The standby capture reports currentPhase "".
    dryer = _make_dryer(_load("dryer_MGD7205RR0_state.json"), _W11771436, "MGD7205RR0")
    assert _phase_flags(dryer) == dict.fromkeys(_FLAGS, False)


# Getters with no wire value whose meaning is known. The running MED7205RW0
# snapshot carries dryLevel, sound.cycleSignal and a cycleName, so any of these
# that went back to decoding the state would answer instead of raising.
@pytest.mark.parametrize(
    "getter",
    [
        Dryer.get_cycle_status_airflow_status,
        Dryer.get_cycle_status_damp,
        Dryer.get_cycle_status_limited_cycle,
        Dryer.get_cycle_status_wet,
        Dryer.get_dryness,
        Dryer.get_cycle_count,
        Dryer.get_damp_notification_tone_volume,
        Dryer.get_alert_tone_volume,
        Dryer.get_cycle_changeable,
        Dryer.get_static_guard_changeable,
    ],
    ids=lambda getter: getter.__name__,
)
def test_unconfirmed_getter_raises(getter: Callable[[Dryer], object]) -> None:
    with pytest.raises(NotImplementedError):
        getter(_med7205rw0())


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("normal", Cycle.Normal),
        # The Normal position on a YMED7205RF0's dial; W11771436 lists no
        # "normal" cycle.
        ("ecoEnergy", Cycle.Normal),
        ("delicates", Cycle.Delicates),
        ("towels", Cycle.Towels),
        ("steamRefresh", Cycle.SteamRefresh),
        ("bulky", Cycle.BulkyItems),
        ("sanitize1", Cycle.Sanitize),
        ("quickDryCottons", Cycle.QuickDry),
        ("timed40", Cycle.TimedDry),
    ],
)
def test_cycle_maps(value: str, expected: Cycle) -> None:
    dryer = _med7205rw0()
    dryer.update_state({"dryer": {"cycleName": value}})
    assert dryer.get_cycle() is expected


def test_eco_energy_is_unknown_beside_a_normal_cycle() -> None:
    # W11804872 lists ecoEnergy and normal as two cycles:
    # https://github.com/abmantis/whirlpool-sixth-sense/pull/167#issuecomment-5616074371
    # The trimmed file keeps normal and timed40, so ecoEnergy is added back.
    capability = copy.deepcopy(_CAPABILITY)
    cycles = capability["cavities"]["dryer"]["cycles"]
    cycles["ecoEnergy"] = copy.deepcopy(cycles["normal"])
    dryer = _make_dryer(capability=capability)
    dryer.update_state({"dryer": {"cycleName": "ecoEnergy"}})
    assert dryer.get_cycle() is None
    dryer.update_state({"dryer": {"cycleName": "normal"}})
    assert dryer.get_cycle() is Cycle.Normal


# heavyLarge1, whitesNormal and jeansDenim are enumerated in capability files,
# but no dryer has reported them and none is its Cycle member's word. The rest
# are the HTTP backend's names, never seen on AWS.
@pytest.mark.parametrize(
    "value",
    [
        "heavyLarge1",
        "whitesNormal",
        "jeansDenim",
        "regular",
        "heavyDuty",
        "wrinkleControl",
        "bulkyItems",
        "quickDry",
        "sanitize",
        "timedDry",
        "whites",
    ],
)
def test_unconfirmed_cycle_is_unknown(value: str) -> None:
    dryer = _med7205rw0()
    dryer.update_state({"dryer": {"cycleName": value}})
    assert dryer.get_cycle() is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("high", Temperature.Hot),
        ("medium", Temperature.Warm),
        ("airOnly", Temperature.Air),
    ],
)
def test_temperature_maps(value: str, expected: Temperature) -> None:
    dryer = _med7205rw0()
    dryer.update_state({"dryer": {"dryTemperature": value}})
    assert dryer.get_temperature() is expected


# low and extraLow are enumerated in W11771436, but no dryer has reported them
# and neither is a Temperature member's word. The rest are the HTTP backend's
# names, never seen on AWS.
@pytest.mark.parametrize(
    "value", ["low", "extraLow", "air", "cool", "warm", "warmHigh", "hot"]
)
def test_unconfirmed_temperature_is_unknown(value: str) -> None:
    dryer = _med7205rw0()
    dryer.update_state({"dryer": {"dryTemperature": value}})
    assert dryer.get_temperature() is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("off", WrinkleShield.Off),
        ("on", WrinkleShield.On),
        ("onWithSteam", WrinkleShield.OnWithSteam),
        ("x", None),
    ],
)
def test_wrinkle_shield_maps(value: str, expected: WrinkleShield | None) -> None:
    dryer = _med7205rw0()
    dryer.update_state({"dryer": {"wrinkleShield": value}})
    assert dryer.get_wrinkle_shield() is expected


def _freeze_clock(monkeypatch: pytest.MonkeyPatch, now: int) -> None:
    monkeypatch.setattr(time, "time", lambda: float(now))


# The running MED7205RW0 snapshot predicts the timed40 cycle's end at
# 1789349404. cycleTime.time stayed at 2400 from start to end, so it is the
# cycle's length, not a countdown. The end snapshot's timePaused, 1789349443,
# puts the finish 39 s past the prediction.
_MED7205RW0_PREDICTED_END = 1789349404


def test_time_remaining_counts_down_to_the_predicted_end(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _freeze_clock(monkeypatch, _MED7205RW0_PREDICTED_END - 1200)
    dryer = _med7205rw0()
    assert dryer.get_time_remaining() == 1200
    assert dryer.get_cycle_time_complete() == _MED7205RW0_PREDICTED_END


def test_time_remaining_stops_at_zero_past_the_predicted_end(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _freeze_clock(monkeypatch, 1789349443)
    dryer = _med7205rw0()
    assert dryer.get_time_remaining() == 0
    assert dryer.get_cycle_time_complete() == _MED7205RW0_PREDICTED_END


def test_time_is_unknown_while_the_cycle_time_is_not_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The gate reads cycleTime.state, not applianceState. Every MED7205RW0
    # sample pairs the two, so this split is built, not captured: the
    # programming snapshot with only applianceState moved on. Both getters
    # return None, so callers must handle None.
    state = _load("dryer_MED7205RW0_programming.json")
    _freeze_clock(monkeypatch, state["dryer"]["cycleTime"]["timeComplete"] - 600)
    dryer = _make_dryer(state, _W11771436, "MED7205RW0")
    dryer.update_state({"dryer": {"applianceState": "running"}})
    assert dryer.get_machine_state() == MachineState.RunningMainCycle
    assert dryer.get_time_remaining() is None
    assert dryer.get_cycle_time_complete() is None


# Outside a running cycle nothing counts down: the idle captures carry a
# leftover timeComplete (2022 on the MED7205RW0), and the paused and end
# snapshots keep the stopped cycle's prediction. The clock sits ten minutes
# before each snapshot's own timeComplete, so reading it would show a 600 s
# countdown.
@pytest.mark.parametrize(
    ("state_file", "model_number"),
    [
        pytest.param("dryer_MGD7205RR0_state.json", "MGD7205RR0", id="standby"),
        pytest.param(
            "dryer_MED7205RW0_programming.json", "MED7205RW0", id="programming"
        ),
        pytest.param("dryer_MED7205RW0_paused.json", "MED7205RW0", id="paused"),
        pytest.param("dryer_MED7205RW0_end.json", "MED7205RW0", id="end"),
    ],
)
def test_time_is_unknown_outside_a_running_cycle(
    monkeypatch: pytest.MonkeyPatch, state_file: str, model_number: str
) -> None:
    state = _load(state_file)
    _freeze_clock(monkeypatch, state["dryer"]["cycleTime"]["timeComplete"] - 600)
    dryer = _make_dryer(state, _W11771436, model_number)
    assert dryer.get_time_remaining() is None
    assert dryer.get_cycle_time_complete() is None


# timedDry is the selected length in minutes, sent as a string, and the ABC
# reports seconds. The MED7205RW0 timed40 cycle reported "40".
def test_manual_dry_time_is_in_seconds() -> None:
    assert _med7205rw0().get_manual_dry_time() == 2400


def test_manual_dry_time_does_not_read_the_cycle_length() -> None:
    # JReich's quickDryCottons cycle reported "15"; the snapshot's
    # cycleTime.time stays at 2400.
    dryer = _med7205rw0()
    dryer.update_state({"dryer": {"timedDry": "15"}})
    assert dryer.get_manual_dry_time() == 900


def test_unparseable_manual_dry_time_is_unknown() -> None:
    dryer = _med7205rw0()
    dryer.update_state({"dryer": {"timedDry": "abc"}})
    assert dryer.get_manual_dry_time() is None


def test_manual_dry_time_is_unknown_without_the_key() -> None:
    # The programming snapshot, a bulky cycle, carries no timedDry key.
    dryer = _med7205rw0("dryer_MED7205RW0_programming.json")
    assert dryer.get_manual_dry_time() is None


def test_live_eco_energy_cycle_reads_normal() -> None:
    # A live capture of a YMED7205RF0 running an ecoEnergy cycle on 2026-10-02,
    # with the dial on Normal. The state is what update_state held after a getState
    # reply: the capture's replies and dt pushes, merged in order. The
    # top-level payload.currentTime came from one of those pushes and is kept.
    dryer = _make_dryer(
        _load("dryer_YMED7205RF0_running.json"), _W11771436, "YMED7205RF0"
    )
    assert dryer.get_machine_state() == MachineState.RunningMainCycle
    assert dryer.get_cycle() is Cycle.Normal
