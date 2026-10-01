"""Tests for laundry capability profiles.

The capability fixtures are trimmed captures from a Maytag MGD7020RF0 dryer
(part W11804872) and MFW7020RF0 washer (part W11812024): the real `appliance`
features and `cavities` structure, reduced to two cycles each.
"""

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
from whirlpool.dryer import Cycle, Dryness, Temperature
from whirlpool.types import ApplianceInfo

_DATA_DIR = Path(__file__).parent.parent / "data" / "awsiot"

DRYER_CAPABILITY = json.loads((_DATA_DIR / "dryer_capability.json").read_text())
WASHER_CAPABILITY = json.loads((_DATA_DIR / "washer_capability.json").read_text())
DRYER_STATE = json.loads((_DATA_DIR / "dryer_state.json").read_text())


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
    profile = parse_laundry_capability_profile(DRYER_CAPABILITY, "dryer")
    dryer = Dryer(mqtt, info, profile)
    dryer.update_state(DRYER_STATE)
    return dryer


# --------------------------------------------------------------------------
# Cavity discrimination
# --------------------------------------------------------------------------


def test_dryer_capability_declares_only_a_dryer_cavity() -> None:
    assert has_dryer_cavity(DRYER_CAPABILITY)
    assert not has_washer_cavity(DRYER_CAPABILITY)
    assert not has_microwave_cavity(DRYER_CAPABILITY)


def test_washer_capability_declares_only_a_washer_cavity() -> None:
    assert has_washer_cavity(WASHER_CAPABILITY)
    assert not has_dryer_cavity(WASHER_CAPABILITY)


@pytest.mark.parametrize(
    "raw", [{"partNumber": "X"}, {"cavities": "not-a-dict"}, {"cavities": {}}]
)
def test_malformed_capability_declares_no_cavity(raw: dict) -> None:
    assert not has_dryer_cavity(raw)
    assert not has_washer_cavity(raw)


# --------------------------------------------------------------------------
# Profile parsing
# --------------------------------------------------------------------------


def test_profile_reads_part_number_and_features() -> None:
    profile = parse_laundry_capability_profile(DRYER_CAPABILITY, "dryer")
    assert profile.part_number == "W11804872"
    assert profile.cavity == "dryer"
    assert profile.supports_control_lock
    assert profile.supports_remote_start


def test_profile_collects_cycles() -> None:
    profile = parse_laundry_capability_profile(DRYER_CAPABILITY, "dryer")
    assert set(profile.cycles) == {"normal", "timed40"}


def test_option_phases_reports_declared_phases() -> None:
    profile = parse_laundry_capability_profile(DRYER_CAPABILITY, "dryer")
    assert profile.option_phases("normal", "dryLevel") == ("sensing", "petsCare")


def test_option_declared_but_never_changeable_is_empty() -> None:
    profile = parse_laundry_capability_profile(DRYER_CAPABILITY, "dryer")
    assert profile.option_phases("timed40", "staticGuardEnable") == ()


def test_option_absent_from_cycle_is_none() -> None:
    profile = parse_laundry_capability_profile(DRYER_CAPABILITY, "dryer")
    # timed40 is a timed cycle: it declares no sensor dryness level.
    assert profile.option_phases("timed40", "dryLevel") is None


def test_parsing_the_wrong_cavity_raises() -> None:
    with pytest.raises(CapabilityDownloadError):
        parse_laundry_capability_profile(DRYER_CAPABILITY, "washer")


# --------------------------------------------------------------------------
# option_changeable semantics
# --------------------------------------------------------------------------


def test_option_changeable_while_idle() -> None:
    profile = parse_laundry_capability_profile(DRYER_CAPABILITY, "dryer")
    assert profile.option_changeable("normal", "dryLevel", None) is True


def test_option_changeable_only_during_declared_phases() -> None:
    profile = parse_laundry_capability_profile(DRYER_CAPABILITY, "dryer")
    assert profile.option_changeable("normal", "dryLevel", "sensing") is True
    assert profile.option_changeable("normal", "dryLevel", "coolDown") is False


def test_option_changeable_is_false_for_unknown_cycle_or_option() -> None:
    profile = parse_laundry_capability_profile(DRYER_CAPABILITY, "dryer")
    assert profile.option_changeable("noSuchCycle", "dryLevel", None) is False
    assert profile.option_changeable("normal", "noSuchOption", None) is False
    assert profile.option_changeable(None, "dryLevel", None) is False


# --------------------------------------------------------------------------
# Dryer wiring
# --------------------------------------------------------------------------


def test_changeable_flags_resolve_with_a_profile() -> None:
    # dryer_state.json is idle on the "normal" cycle, which declares every one
    # of these options with a non-empty changeable phase list.
    dryer = _make_dryer()
    assert dryer.get_dryness_changeable() is True
    assert dryer.get_temperature_changeable() is True
    assert dryer.get_extra_power_changeable() is True
    assert dryer.get_steam_changeable() is True


def test_changeable_flags_follow_the_selected_cycle() -> None:
    # timed40 is a timed cycle: it offers no sensor dryness at all, and
    # declares steam with an empty changeable list.
    dryer = _make_dryer()
    dryer.update_state({"dryer": {"cycleName": "timed40"}})
    assert dryer.get_dryness_changeable() is False
    assert dryer.get_steam_changeable() is False
    # ...but the timed-dry length itself becomes adjustable.
    assert dryer.get_manual_dry_time_changeable() is True


def test_cycle_changeable_tracks_machine_state() -> None:
    assert _make_dryer().get_cycle_changeable() is True


def test_alert_tone_volume_decodes_cycle_signal() -> None:
    assert _make_dryer().get_alert_tone_volume() == 3


def test_capability_file_vocabularies_decode() -> None:
    dryer = _make_dryer()
    assert dryer.get_cycle() is Cycle.Normal
    assert dryer.get_dryness() is Dryness.Normal
    # MGD7020RF0 declares airOnly/low/medium/high, not the HTTP backend's names.
    assert dryer.get_temperature() is Temperature.Warm
