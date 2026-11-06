"""Tests for laundry capability profiles."""

import json
from pathlib import Path

import pytest

from whirlpool.awsiot.capabilities import (
    CapabilityDownloadError,
    has_dryer_cavity,
    has_microwave_cavity,
    has_washer_cavity,
    parse_laundry_capability_profile,
)

_DATA_DIR = Path(__file__).parent.parent / "data" / "awsiot"

W11771387 = json.loads((_DATA_DIR / "capability_washer_W11771387.json").read_text())
W11812024 = json.loads((_DATA_DIR / "washer_capability.json").read_text())


@pytest.mark.parametrize("raw", [W11771387, W11812024], ids=["W11771387", "W11812024"])
def test_washer_capability_declares_only_a_washer_cavity(raw: dict) -> None:
    assert has_washer_cavity(raw)
    assert not has_dryer_cavity(raw)
    assert not has_microwave_cavity(raw)


def test_dryer_cavity_is_detected() -> None:
    raw = {"partNumber": "X", "cavities": {"dryer": {}}}
    assert has_dryer_cavity(raw)
    assert not has_washer_cavity(raw)


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
