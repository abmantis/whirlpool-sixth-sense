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
# A trimmed W11804872 capability file.
_CAPABILITY = _load("dryer_capability.json")
# The part of the MGD7205RR0, MED7205RW0 and YMED7205RF0 captures.
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


# Every applianceState the dryer map keeps.
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


# Not applianceState values on any AWS dryer.
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


# Every currentPhase spelling the dryer maps (phase None: as captured).
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
    assert _phase_flags(_running_med7205rw0("petsCare")) == dict.fromkeys(_FLAGS, False)


def test_phase_flags_are_unknown_without_a_phase() -> None:
    # No currentPhase key at all.
    dryer = _make_dryer(
        {"dryer": {"applianceState": "running"}}, _W11771436, "MED7205RW0"
    )
    assert _phase_flags(dryer) == dict.fromkeys(_FLAGS, None)


def test_empty_phase_sets_no_flag() -> None:
    dryer = _make_dryer(_load("dryer_MGD7205RR0_state.json"), _W11771436, "MGD7205RR0")
    assert _phase_flags(dryer) == dict.fromkeys(_FLAGS, False)


# The running snapshot carries dryLevel, sound.cycleSignal and a cycleName, so a
# getter that decoded them would answer instead of raising.
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
        ("ecoEnergy", Cycle.Normal),
        ("delicates", Cycle.Delicates),
        ("towels", Cycle.Towels),
        ("steamRefresh", Cycle.SteamRefresh),
        ("bulky", Cycle.BulkyItems),
        ("quickDryCottons", Cycle.QuickDry),
        ("timed40", Cycle.TimedDry),
    ],
)
def test_cycle_maps(value: str, expected: Cycle) -> None:
    dryer = _med7205rw0()
    dryer.update_state({"dryer": {"cycleName": value}})
    assert dryer.get_cycle() is expected


def test_eco_energy_is_unknown_beside_a_normal_cycle() -> None:
    # W11804872 lists ecoEnergy beside normal; the trimmed file drops it.
    capability = copy.deepcopy(_CAPABILITY)
    cycles = capability["cavities"]["dryer"]["cycles"]
    cycles["ecoEnergy"] = copy.deepcopy(cycles["normal"])
    dryer = _make_dryer(capability=capability)
    dryer.update_state({"dryer": {"cycleName": "ecoEnergy"}})
    assert dryer.get_cycle() is None
    dryer.update_state({"dryer": {"cycleName": "normal"}})
    assert dryer.get_cycle() is Cycle.Normal


@pytest.mark.parametrize(
    "value",
    [
        "sanitize1",
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
        ("airOnly", Temperature.Air),
    ],
)
def test_temperature_maps(value: str, expected: Temperature) -> None:
    dryer = _med7205rw0()
    dryer.update_state({"dryer": {"dryTemperature": value}})
    assert dryer.get_temperature() is expected


# W11771436 has four heat levels (extraLow, low, medium, high), so which
# Temperature each of the lower three is stays open.
@pytest.mark.parametrize(
    "value",
    ["medium", "low", "extraLow", "air", "cool", "warm", "warmHigh", "hot"],
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


# The running snapshot's timeComplete.
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
    _freeze_clock(monkeypatch, _MED7205RW0_PREDICTED_END + 39)
    dryer = _med7205rw0()
    assert dryer.get_time_remaining() == 0
    assert dryer.get_cycle_time_complete() == _MED7205RW0_PREDICTED_END


def test_time_is_unknown_while_the_cycle_time_is_not_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Built: the programming snapshot with only applianceState moved on.
    state = _load("dryer_MED7205RW0_programming.json")
    _freeze_clock(monkeypatch, state["dryer"]["cycleTime"]["timeComplete"] - 600)
    dryer = _make_dryer(state, _W11771436, "MED7205RW0")
    dryer.update_state({"dryer": {"applianceState": "running"}})
    assert dryer.get_machine_state() == MachineState.RunningMainCycle
    assert dryer.get_time_remaining() is None
    assert dryer.get_cycle_time_complete() is None


# The clock sits ten minutes before each snapshot's timeComplete, so reading it
# would show a 600 s countdown.
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


def test_manual_dry_time_is_in_seconds() -> None:
    assert _med7205rw0().get_manual_dry_time() == 2400


def test_manual_dry_time_does_not_read_the_cycle_length() -> None:
    dryer = _med7205rw0()
    dryer.update_state({"dryer": {"timedDry": "15"}})
    assert dryer.get_manual_dry_time() == 900


def test_unparseable_manual_dry_time_is_unknown() -> None:
    dryer = _med7205rw0()
    dryer.update_state({"dryer": {"timedDry": "abc"}})
    assert dryer.get_manual_dry_time() is None


def test_manual_dry_time_is_unknown_without_the_key() -> None:
    dryer = _med7205rw0("dryer_MED7205RW0_programming.json")
    assert dryer.get_manual_dry_time() is None


def test_live_eco_energy_cycle_reads_normal() -> None:
    # A YMED7205RF0 with the dial on Normal.
    dryer = _make_dryer(
        _load("dryer_YMED7205RF0_running.json"), _W11771436, "YMED7205RF0"
    )
    assert dryer.get_machine_state() == MachineState.RunningMainCycle
    assert dryer.get_cycle() is Cycle.Normal
