"""Tests for laundry capability profiles."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from whirlpool.awsiot.capabilities import (
    CapabilityDownloadError,
    has_dryer_cavity,
    has_microwave_cavity,
    has_washer_cavity,
    parse_laundry_capability_profile,
)
from whirlpool.awsiot.dryer import Dryer
from whirlpool.types import ApplianceInfo

_DATA_DIR = Path(__file__).parent.parent / "data" / "awsiot"

W11771387 = json.loads((_DATA_DIR / "capability_washer_W11771387.json").read_text())
W11812024 = json.loads((_DATA_DIR / "washer_capability.json").read_text())
W11804872 = json.loads((_DATA_DIR / "dryer_capability.json").read_text())
DRYER_STATE = json.loads((_DATA_DIR / "dryer_state.json").read_text())


@pytest.mark.parametrize("raw", [W11771387, W11812024], ids=["W11771387", "W11812024"])
def test_washer_capability_declares_only_a_washer_cavity(raw: dict) -> None:
    assert has_washer_cavity(raw)
    assert not has_dryer_cavity(raw)
    assert not has_microwave_cavity(raw)


def test_dryer_capability_declares_only_a_dryer_cavity() -> None:
    assert has_dryer_cavity(W11804872)
    assert not has_washer_cavity(W11804872)
    assert not has_microwave_cavity(W11804872)


@pytest.mark.parametrize(
    "raw", [{"partNumber": "X"}, {"cavities": "not-a-dict"}, {"cavities": {}}]
)
def test_malformed_capability_declares_no_cavity(raw: dict) -> None:
    assert not has_dryer_cavity(raw)
    assert not has_washer_cavity(raw)


def test_profile_reads_part_number_and_features() -> None:
    profile = parse_laundry_capability_profile(W11812024, "washer")
    assert profile.part_number == "W11812024"
    assert profile.cavity == "washer"
    assert profile.supports_control_lock
    assert profile.supports_remote_start


def test_profile_without_control_lock_feature() -> None:
    profile = parse_laundry_capability_profile(W11771387, "washer")
    assert not profile.supports_control_lock
    assert profile.supports_remote_start


def test_profile_collects_cycles() -> None:
    profile = parse_laundry_capability_profile(W11812024, "washer")
    assert set(profile.cycles) == {"normal", "delicates"}


def test_option_phases_reports_declared_phases() -> None:
    profile = parse_laundry_capability_profile(W11771387, "washer")
    assert profile.option_phases("regularNormal", "soilLevel") == (
        "sensing",
        "filling",
        "preWash",
    )


def test_option_declared_but_never_changeable_is_empty() -> None:
    profile = parse_laundry_capability_profile(W11771387, "washer")
    assert profile.option_phases("drainAndSpin", "spinSpeed") == ()


def test_option_absent_from_cycle_is_none() -> None:
    profile = parse_laundry_capability_profile(W11771387, "washer")
    assert profile.option_phases("drainAndSpin", "soilLevel") is None


def test_parsing_the_wrong_cavity_raises() -> None:
    with pytest.raises(CapabilityDownloadError):
        parse_laundry_capability_profile(W11771387, "dryer")


def test_option_changeable_only_during_declared_phases() -> None:
    profile = parse_laundry_capability_profile(W11771387, "washer")
    assert profile.option_changeable("regularNormal", "soilLevel", "sensing") is True
    assert profile.option_changeable("regularNormal", "soilLevel", "washing") is False


def test_option_changeable_is_false_without_a_phase() -> None:
    profile = parse_laundry_capability_profile(W11771387, "washer")
    assert profile.option_changeable("regularNormal", "soilLevel", None) is False


def test_option_changeable_is_false_for_unknown_cycle_or_option() -> None:
    profile = parse_laundry_capability_profile(W11771387, "washer")
    assert profile.option_changeable("noSuchCycle", "soilLevel", "sensing") is False
    assert (
        profile.option_changeable("regularNormal", "noSuchOption", "sensing") is False
    )
    assert profile.option_changeable(None, "soilLevel", "sensing") is False
    assert profile.option_changeable("drainAndSpin", "spinSpeed", "spin") is False


def test_dryer_profile_reads_cycles_and_phases() -> None:
    profile = parse_laundry_capability_profile(W11804872, "dryer")
    assert profile.part_number == "W11804872"
    assert profile.cavity == "dryer"
    assert set(profile.cycles) == {"normal", "timed40"}
    assert profile.option_phases("normal", "dryLevel") == ("sensing", "petsCare")
    assert profile.option_phases("timed40", "steam") == ()
    # A timed cycle declares no sensor dryness level.
    assert profile.option_phases("timed40", "dryLevel") is None


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
    dryer = Dryer(mqtt, info, parse_laundry_capability_profile(W11804872, "dryer"))
    dryer.update_state(DRYER_STATE)
    return dryer


def test_dryer_changeable_flags_are_false_in_standby() -> None:
    # dryer_state.json is in standby on "normal", with currentPhase "".
    dryer = _make_dryer()
    assert dryer.get_dryness_changeable() is False
    assert dryer.get_temperature_changeable() is False
    assert dryer.get_wrinkle_shield_changeable() is False


def test_dryer_changeable_flags_follow_the_phase() -> None:
    dryer = _make_dryer()
    dryer.update_state(
        {"dryer": {"applianceState": "running", "currentPhase": "sensing"}}
    )
    assert dryer.get_dryness_changeable() is True
    assert dryer.get_extra_power_changeable() is True
    dryer.update_state({"dryer": {"currentPhase": "coolDown"}})
    assert dryer.get_dryness_changeable() is False
    assert dryer.get_wrinkle_shield_changeable() is True


def test_dryer_changeable_flags_follow_the_cycle() -> None:
    dryer = _make_dryer()
    dryer.update_state(
        {
            "dryer": {
                "applianceState": "running",
                "currentPhase": "dry",
                "cycleName": "timed40",
            }
        }
    )
    assert dryer.get_dryness_changeable() is False
    assert dryer.get_steam_changeable() is False
    assert dryer.get_manual_dry_time_changeable() is True
