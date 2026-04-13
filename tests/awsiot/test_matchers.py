from typing import Any

import pytest

from whirlpool_aws.awsiot.capabilities import parse_capability_profile
from whirlpool_aws.awsiot.matchers import (
    all_of,
    any_of,
    has_addressee,
    has_command,
    has_feature,
    model_prefix,
    not_,
    thing_category,
)


@pytest.fixture
def profile(capability_mwo_raw: dict[str, Any]):
    return parse_capability_profile(capability_mwo_raw)


@pytest.fixture
def profile_no_hood(capability_mwo_no_hood_raw: dict[str, Any]):
    return parse_capability_profile(capability_mwo_no_hood_raw)


def test_has_feature(profile, thing_mwo):
    assert has_feature("microwaveOven")(profile, thing_mwo) is True
    assert has_feature("deepFryer")(profile, thing_mwo) is False


def test_has_addressee(profile, profile_no_hood, thing_mwo):
    assert has_addressee("hoodFan")(profile, thing_mwo) is True
    assert has_addressee("hoodFan")(profile_no_hood, thing_mwo) is False


def test_has_command(profile, thing_mwo):
    assert has_command("primaryCavity", "microwave")(profile, thing_mwo) is True
    assert has_command("primaryCavity", "detonate")(profile, thing_mwo) is False


def test_model_prefix(profile, thing_mwo):
    assert model_prefix("KMML")(profile, thing_mwo) is True
    assert model_prefix("ABCD")(profile, thing_mwo) is False


def test_thing_category(profile, thing_mwo):
    assert thing_category("cooking")(profile, thing_mwo) is True
    assert thing_category("laundry")(profile, thing_mwo) is False


def test_all_of_any_of_not(profile, profile_no_hood, thing_mwo):
    combined = all_of(has_feature("microwaveOven"), has_addressee("primaryCavity"))
    assert combined(profile, thing_mwo) is True

    either = any_of(has_addressee("hoodFan"), has_feature("nope"))
    assert either(profile, thing_mwo) is True
    assert either(profile_no_hood, thing_mwo) is False

    negated = not_(has_addressee("hoodFan"))
    assert negated(profile, thing_mwo) is False
    assert negated(profile_no_hood, thing_mwo) is True
