import logging
from typing import Any

import pytest

from whirlpool.awsiot.capabilities import parse_capability_profile
from whirlpool.awsiot.factory import ApplianceFactory, register_appliance
from whirlpool.awsiot.matchers import has_addressee, has_feature
from whirlpool.types import ApplianceInfo


class _StubBase:
    def __init__(
        self,
        mqtt: Any,
        appliance_info: ApplianceInfo,
        capability_profile: Any,
    ) -> None:
        self.mqtt = mqtt
        self.info = appliance_info
        self.profile = capability_profile


@pytest.fixture
def info() -> ApplianceInfo:
    return ApplianceInfo(
        said="S", name="n", category="cooking",
        model_number="M", serial_number="X",
    )


@pytest.fixture
def mwo_profile(capability_mwo_raw):
    return parse_capability_profile(capability_mwo_raw)


def test_registration_and_priority(mwo_profile, thing_mwo, info):
    factory = ApplianceFactory()

    class HighMatch(_StubBase):
        pass

    class LowMatch(_StubBase):
        pass

    factory.register(
        LowMatch, matcher=has_addressee("primaryCavity"), priority=1
    )
    factory.register(
        HighMatch,
        matcher=lambda p, t: has_addressee("primaryCavity")(p, t)
        and has_feature("microwaveOven")(p, t),
        priority=10,
    )

    built = factory.build(object(), mwo_profile, thing_mwo, info)
    assert isinstance(built, HighMatch)


def test_build_returns_none_when_no_matcher_fires(mwo_profile, thing_mwo, info):
    factory = ApplianceFactory()

    class Nada(_StubBase):
        pass

    factory.register(Nada, matcher=has_feature("nonexistent"), priority=5)
    assert factory.build(object(), mwo_profile, thing_mwo, info) is None


def test_tie_break_first_registered_wins(
    mwo_profile, thing_mwo, info, caplog: pytest.LogCaptureFixture
):
    factory = ApplianceFactory()

    class First(_StubBase):
        pass

    class Second(_StubBase):
        pass

    factory.register(First, matcher=has_addressee("primaryCavity"), priority=5)
    factory.register(Second, matcher=has_addressee("primaryCavity"), priority=5)

    with caplog.at_level(logging.WARNING, logger="whirlpool.awsiot.factory"):
        built = factory.build(object(), mwo_profile, thing_mwo, info)
    assert isinstance(built, First)
    assert any("tie" in r.message.lower() for r in caplog.records)


def test_decorator_registers_in_default_factory(mwo_profile, thing_mwo, info):
    from whirlpool.awsiot.factory import DEFAULT_FACTORY

    marker: list[type] = []

    @register_appliance(
        matcher=has_feature("microwaveOven"), priority=100, factory=DEFAULT_FACTORY,
    )
    class Decorated(_StubBase):
        pass

    marker.append(Decorated)
    built = DEFAULT_FACTORY.build(object(), mwo_profile, thing_mwo, info)
    # Decorated should win vs anything else already registered at a lower priority.
    assert isinstance(built, marker[0])
