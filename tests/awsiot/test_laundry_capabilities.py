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


@pytest.mark.parametrize(
    ("raw", "part_number"),
    [(W11771387, "W11771387"), (W11812024, "W11812024")],
    ids=["W11771387", "W11812024"],
)
def test_profile_reads_part_number_and_cavity(raw: dict, part_number: str) -> None:
    profile = parse_laundry_capability_profile(raw, "washer")
    assert profile.part_number == part_number
    assert profile.cavity == "washer"


def test_parsing_the_wrong_cavity_raises() -> None:
    with pytest.raises(CapabilityDownloadError):
        parse_laundry_capability_profile(W11771387, "dryer")
