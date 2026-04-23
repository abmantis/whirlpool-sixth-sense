import copy
import logging

import pytest

from whirlpool.awsiot.capabilities import parse_capability_profile
from whirlpool.awsiot.microwave import Microwave
from whirlpool.microwave import (
    HoodFanSpeed,
    HoodLightColor,
    HoodLightLevel,
    MicrowaveCavityState,
    MicrowaveDoorStatus,
    RecipeId,
)
from whirlpool.types import ApplianceInfo


@pytest.fixture
def info() -> ApplianceInfo:
    return ApplianceInfo(
        said="SAIDMWO",
        name="Test MWO",
        category="cooking",
        model_number="KMMC5019JBS",
        serial_number="D1",
    )


@pytest.fixture
def profile(capability_mwo_raw):
    return parse_capability_profile(capability_mwo_raw)


@pytest.fixture
def profile_no_hood(capability_mwo_no_hood_raw):
    return parse_capability_profile(capability_mwo_no_hood_raw)


@pytest.fixture
async def mwo(fake_mqtt, profile, info, state_mwo_full) -> Microwave:
    await fake_mqtt.connect()
    app = Microwave(
        fake_mqtt,
        info,
        profile,
        initial_state_timeout=0.05,
        heartbeat_interval=0,
    )
    await app.connect()
    # Seed state directly for getter tests.
    app._state = copy.deepcopy(state_mwo_full)
    return app


# --- getters -------------------------------------------------------------

def test_cavity_state_idle(mwo: Microwave):
    assert mwo.get_cavity_state() == MicrowaveCavityState.Idle


def test_cavity_state_cooking(mwo: Microwave, state_mwo_cooking):
    mwo._state = copy.deepcopy(state_mwo_cooking)
    assert mwo.get_cavity_state() == MicrowaveCavityState.Cooking


def test_cavity_state_unknown_for_unrecognized(mwo: Microwave):
    mwo._state["primaryCavity"]["cavityState"] = "???"
    assert mwo.get_cavity_state() == MicrowaveCavityState.Unknown


def test_door_status(mwo: Microwave):
    assert mwo.get_door_status() == MicrowaveDoorStatus.Closed


def test_cavity_light(mwo: Microwave):
    assert mwo.get_cavity_light() is False


def test_mwo_power_level(mwo: Microwave, state_mwo_cooking):
    mwo._state = copy.deepcopy(state_mwo_cooking)
    assert mwo.get_mwo_power_level() == 80


def test_cook_timer_total_and_remaining(mwo: Microwave, state_mwo_cooking):
    mwo._state = copy.deepcopy(state_mwo_cooking)
    assert mwo.get_cook_timer_total_seconds() == 30
    # Remaining may be negative when timeComplete is in the past —
    # the getter clamps to >= 0.
    remaining = mwo.get_cook_timer_remaining_seconds()
    assert remaining is None or remaining >= 0


def test_hood_fan_speed(mwo: Microwave):
    assert mwo.get_hood_fan_speed() == HoodFanSpeed.Off


def test_hood_light_level(mwo: Microwave):
    assert mwo.get_hood_light_level() == HoodLightLevel.Medium


def test_hood_light_color(mwo: Microwave):
    assert mwo.get_hood_light_color() == HoodLightColor.WarmWhite


def test_remote_start_enabled(mwo: Microwave):
    assert mwo.get_remote_start_enabled() is True


def test_control_locked(mwo: Microwave):
    assert mwo.get_control_locked() is False


# --- setters -------------------------------------------------------------

async def test_set_cavity_light_publishes_command(mwo: Microwave, fake_mqtt):
    fake_mqtt.clear_published()
    ok = await mwo.set_cavity_light(True)
    assert ok is True
    _, payload = fake_mqtt.published[-1]
    assert payload["payload"]["addressee"] == "primaryCavity"
    assert payload["payload"]["command"] == "set"
    assert payload["payload"]["cavityLight"] is True


async def test_set_hood_fan_speed_publishes_command(mwo: Microwave, fake_mqtt):
    fake_mqtt.clear_published()
    ok = await mwo.set_hood_fan_speed(HoodFanSpeed.High)
    assert ok is True
    _, payload = fake_mqtt.published[-1]
    assert payload["payload"]["addressee"] == "hoodFan"
    assert payload["payload"]["command"] == "set"
    assert payload["payload"]["value"] == "high"


async def test_set_hood_light_level(mwo: Microwave, fake_mqtt):
    fake_mqtt.clear_published()
    await mwo.set_hood_light_level(HoodLightLevel.Medium)
    _, payload = fake_mqtt.published[-1]
    assert payload["payload"]["addressee"] == "hoodLight"
    assert payload["payload"]["command"] == "set"
    assert payload["payload"]["value"] == "med"


async def test_set_hood_light_color(mwo: Microwave, fake_mqtt):
    fake_mqtt.clear_published()
    await mwo.set_hood_light_color(HoodLightColor.CoolWhite)
    _, payload = fake_mqtt.published[-1]
    assert payload["payload"]["addressee"] == "hoodLightColor"
    assert payload["payload"]["command"] == "set"
    assert payload["payload"]["value"] == "coolWhite"


async def test_set_quiet_mode(mwo: Microwave, fake_mqtt):
    fake_mqtt.clear_published()
    ok = await mwo.set_quiet_mode(True)
    assert ok is True
    _, payload = fake_mqtt.published[-1]
    assert payload["payload"]["addressee"] == "quietMode"
    assert payload["payload"]["command"] == "set"
    assert payload["payload"]["value"] is True


async def test_set_control_locked_skipped_when_unsupported(
    mwo: Microwave, fake_mqtt, caplog: pytest.LogCaptureFixture
):
    # The default capability fixture has supportsHmiControlLockout: false.
    fake_mqtt.clear_published()
    with caplog.at_level(logging.WARNING, logger="whirlpool_aws.awsiot.microwave"):
        ok = await mwo.set_control_locked(True)
    assert ok is False
    assert fake_mqtt.published == []


async def test_set_sabbath_mode_skipped_when_unsupported(
    mwo: Microwave, fake_mqtt, caplog: pytest.LogCaptureFixture
):
    # The default capability fixture has no sabbathMode declaration.
    fake_mqtt.clear_published()
    with caplog.at_level(logging.WARNING, logger="whirlpool_aws.awsiot.microwave"):
        ok = await mwo.set_sabbath_mode(True)
    assert ok is False
    assert fake_mqtt.published == []


def test_capability_gates(mwo: Microwave):
    assert mwo.supports_quiet_mode is True
    assert mwo.supports_control_lock is False
    assert mwo.supports_sabbath_mode is False


# --- start_cook validation -----------------------------------------------

async def test_start_cook_happy_path(mwo: Microwave, fake_mqtt):
    fake_mqtt.clear_published()
    ok = await mwo.start_cook(RecipeId.Microwave, 80, 30)
    assert ok is True
    _, payload = fake_mqtt.published[-1]
    body = payload["payload"]
    assert body["addressee"] == "primaryCavity"
    assert body["command"] == "run"
    assert body["recipeID"] == "microwave"
    assert body["mwoPowerLevel"] == 80.0
    assert body["cookTimer"] == {"command": "start", "time": 30}


async def test_start_cook_invalid_power_raises(mwo: Microwave):
    with pytest.raises(ValueError):
        await mwo.start_cook(RecipeId.Microwave, 0, 30)
    with pytest.raises(ValueError):
        await mwo.start_cook(RecipeId.Microwave, 101, 30)


async def test_start_cook_invalid_duration_raises(mwo: Microwave):
    with pytest.raises(ValueError):
        await mwo.start_cook(RecipeId.Microwave, 50, 0)


async def test_start_cook_requires_remote_start(
    mwo: Microwave, fake_mqtt, caplog: pytest.LogCaptureFixture
):
    mwo._state["remoteStartEnable"] = False
    fake_mqtt.clear_published()

    with caplog.at_level(logging.WARNING, logger="whirlpool.awsiot.microwave"):
        ok = await mwo.start_cook(RecipeId.Microwave, 50, 30)
    assert ok is False
    assert fake_mqtt.published == []


async def test_cancel_cook(mwo: Microwave, fake_mqtt):
    fake_mqtt.clear_published()
    ok = await mwo.cancel_cook()
    assert ok is True
    _, payload = fake_mqtt.published[-1]
    assert payload["payload"]["addressee"] == "primaryCavity"
    assert payload["payload"]["command"] == "cancel"


# --- hood feature gating -------------------------------------------------

async def test_hood_fan_getter_returns_none_when_absent(
    fake_mqtt, profile_no_hood, info
):
    await fake_mqtt.connect()
    app = Microwave(
        fake_mqtt,
        info,
        profile_no_hood,
        initial_state_timeout=0.05,
        heartbeat_interval=0,
    )
    await app.connect()
    app._state = {"primaryCavity": {"cavityState": "idle"}}
    assert app.get_hood_fan_speed() is None


async def test_hood_fan_setter_skipped_when_feature_absent(
    fake_mqtt, profile_no_hood, info, caplog: pytest.LogCaptureFixture
):
    await fake_mqtt.connect()
    app = Microwave(
        fake_mqtt,
        info,
        profile_no_hood,
        initial_state_timeout=0.05,
        heartbeat_interval=0,
    )
    await app.connect()
    fake_mqtt.clear_published()

    with caplog.at_level(logging.WARNING, logger="whirlpool.awsiot.microwave"):
        ok = await app.set_hood_fan_speed(HoodFanSpeed.High)
    assert ok is False
    assert fake_mqtt.published == []


# --- state delta merge --------------------------------------------------

async def test_state_delta_flips_cavity_light(mwo: Microwave, fake_mqtt, info):
    await fake_mqtt.inject(
        f"dt/{info.model_number}/{info.said}/state/update",
        {"primaryCavity": {"cavityLight": True}},
    )
    assert mwo.get_cavity_light() is True
    assert mwo.get_door_status() == MicrowaveDoorStatus.Closed  # untouched
