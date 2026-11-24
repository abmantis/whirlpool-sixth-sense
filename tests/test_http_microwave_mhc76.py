"""Over-the-range microwave with a hood on the HTTP API (DDM_COOKING_MHC76_V1, #243).

Snapshots in microwave_mhc76_data.json come from a real Whirlpool WMH78019HZ05
(identifiers redacted), one capture per hood state set on the appliance panel.
"""

import json
import logging
from collections.abc import Callable

import pytest
from aiointercept import aiointercept
from yarl import URL

from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.auth import Auth
from whirlpool.backendselector import BackendSelector
from whirlpool.httpapi.microwave import Microwave
from whirlpool.microwave import (
    HoodFanSpeed,
    HoodLightColor,
    HoodLightLevel,
    MicrowaveCavityState,
    MicrowaveDoorStatus,
)

from . import DATA_DIR

SAID = "SAIDMHC76"


def _microwave(appliances_manager: AppliancesManager, said: str = SAID) -> Microwave:
    mwo = next(m for m in appliances_manager.microwaves if m.said == said)
    assert isinstance(mwo, Microwave)
    return mwo


async def _load_snapshot(
    mwo: Microwave,
    backend_selector: BackendSelector,
    aiointercept_mock: aiointercept,
    snapshot: str,
) -> None:
    with open(DATA_DIR / "microwave_mhc76_data.json") as f:
        payload = json.load(f)[snapshot]
    aiointercept_mock.get(
        backend_selector.get_appliance_data_url(mwo.said), payload=payload
    )
    assert await mwo.fetch_data()


async def test_mhc76_data_model_is_a_microwave(
    appliances_manager: AppliancesManager,
):
    assert SAID in [m.said for m in appliances_manager.microwaves]
    assert SAID not in [o.said for o in appliances_manager.ovens]


async def test_attributes(appliances_manager: AppliancesManager):
    mwo = _microwave(appliances_manager)
    assert mwo.get_online() is True
    assert mwo.get_cavity_state() == MicrowaveCavityState.Idle
    assert mwo.get_door_status() == MicrowaveDoorStatus.Closed
    assert mwo.get_cavity_light() is False
    assert mwo.get_cook_timer_state() == "idle"
    assert mwo.get_hood_fan_speed() == HoodFanSpeed.Off
    assert mwo.get_hood_light_level() == HoodLightLevel.Off
    assert mwo.get_hood_light_color() is None
    assert mwo.supports_hood_fan() is True
    assert mwo.supports_hood_light_level() is True
    assert mwo.supports_hood_light_color() is False


async def test_builtin_microwave_has_no_hood(appliances_manager: AppliancesManager):
    w9 = _microwave(appliances_manager, "SAIDMWO1")
    assert w9.get_hood_fan_speed() is None
    assert w9.get_hood_light_level() is None
    assert w9.supports_hood_fan() is False
    assert w9.supports_hood_light_level() is False


@pytest.mark.parametrize(
    ["snapshot", "fan", "light"],
    [
        ("HOOD_OFF", HoodFanSpeed.Off, HoodLightLevel.Off),
        ("FAN_LOW_LIGHT_LOW", HoodFanSpeed.Low, HoodLightLevel.Low),
        ("FAN_MEDIUM", HoodFanSpeed.Medium, HoodLightLevel.Off),
        # The panel's medium-high and high speeds
        ("FAN_MEDIUM_HIGH", HoodFanSpeed.High, HoodLightLevel.Off),
        ("FAN_HIGH", HoodFanSpeed.Boost, HoodLightLevel.Off),
        ("FAN_MEDIUM_LIGHT_HIGH", HoodFanSpeed.Medium, HoodLightLevel.High),
    ],
)
async def test_real_appliance_hood_snapshots(
    appliances_manager: AppliancesManager,
    backend_selector: BackendSelector,
    aiointercept_mock: aiointercept,
    snapshot: str,
    fan: HoodFanSpeed,
    light: HoodLightLevel,
):
    mwo = _microwave(appliances_manager)
    await _load_snapshot(mwo, backend_selector, aiointercept_mock, snapshot)

    assert mwo.get_hood_fan_speed() == fan
    assert mwo.get_hood_light_level() == light
    # Only the hood changed between these captures
    assert mwo.get_cavity_state() == MicrowaveCavityState.Idle
    assert mwo.get_door_status() == MicrowaveDoorStatus.Closed


@pytest.mark.parametrize(
    ["method", "arguments", "expected_json"],
    [
        (
            Microwave.set_hood_fan_speed,
            {"speed": HoodFanSpeed.Off},
            {"Hood_OperationSetExhaustFanSpeed": "0"},
        ),
        (
            Microwave.set_hood_fan_speed,
            {"speed": HoodFanSpeed.Low},
            {"Hood_OperationSetExhaustFanSpeed": "2"},
        ),
        (
            Microwave.set_hood_fan_speed,
            {"speed": HoodFanSpeed.Medium},
            {"Hood_OperationSetExhaustFanSpeed": "4"},
        ),
        (
            Microwave.set_hood_fan_speed,
            {"speed": HoodFanSpeed.High},
            {"Hood_OperationSetExhaustFanSpeed": "5"},
        ),
        (
            Microwave.set_hood_fan_speed,
            {"speed": HoodFanSpeed.Boost},
            {"Hood_OperationSetExhaustFanSpeed": "6"},
        ),
        (
            Microwave.set_hood_light_level,
            {"level": HoodLightLevel.Off},
            {"Hood_OperationSetSurfaceLight": "0"},
        ),
        (
            Microwave.set_hood_light_level,
            {"level": HoodLightLevel.Low},
            {"Hood_OperationSetSurfaceLight": "2"},
        ),
        (
            Microwave.set_hood_light_level,
            {"level": HoodLightLevel.High},
            {"Hood_OperationSetSurfaceLight": "4"},
        ),
    ],
)
async def test_hood_setters(
    appliances_manager: AppliancesManager,
    auth: Auth,
    backend_selector: BackendSelector,
    aiointercept_mock: aiointercept,
    method: Callable,
    arguments: dict,
    expected_json: dict,
):
    mwo = _microwave(appliances_manager)
    expected_payload = {
        "json": {
            "body": expected_json,
            "header": {"said": mwo.said, "command": "setAttributes"},
        }
    }
    url = backend_selector.appliance_command_url

    aiointercept_mock.post(url, payload=expected_payload)
    assert await getattr(mwo, method.__name__)(**arguments)

    aiointercept_mock.assert_called_with(
        url=url,
        method="POST",
        data=None,
        json=expected_payload["json"],
        headers=auth.create_headers(),
    )
    assert len(aiointercept_mock.requests[("POST", URL(url))]) == 1


async def test_unsupported_hood_values_send_nothing(
    appliances_manager: AppliancesManager,
    backend_selector: BackendSelector,
    aiointercept_mock: aiointercept,
):
    mwo = _microwave(appliances_manager)
    # No medium step on the cooktop light, and no light color on this model
    assert await mwo.set_hood_light_level(HoodLightLevel.Medium) is False
    assert await mwo.set_hood_light_color(HoodLightColor.WarmWhite) is False
    # A built-in microwave has no hood at all
    w9 = _microwave(appliances_manager, "SAIDMWO1")
    assert await w9.set_hood_fan_speed(HoodFanSpeed.Low) is False
    assert await w9.set_hood_light_level(HoodLightLevel.Low) is False
    url = backend_selector.appliance_command_url
    assert ("POST", URL(url)) not in aiointercept_mock.requests


async def test_unknown_hood_values(
    appliances_manager: AppliancesManager,
    backend_selector: BackendSelector,
    aiointercept_mock: aiointercept,
    caplog: pytest.LogCaptureFixture,
):
    mwo = _microwave(appliances_manager)
    with open(DATA_DIR / "microwave_mhc76_data.json") as f:
        payload = json.load(f)["HOOD_OFF"]
    payload["attributes"]["Hood_OperationSetExhaustFanSpeed"]["value"] = "3"
    payload["attributes"]["Hood_OperationSetSurfaceLight"]["value"] = "1"
    aiointercept_mock.get(
        backend_selector.get_appliance_data_url(mwo.said), payload=payload
    )
    assert await mwo.fetch_data()

    with caplog.at_level(logging.DEBUG):
        assert mwo.get_hood_fan_speed() is None
        assert mwo.get_hood_light_level() is None
    assert "Unknown hood fan speed: 3" in caplog.text
    assert "Unknown hood light level: 1" in caplog.text
    # Still a hood, even when the value is unknown
    assert mwo.supports_hood_fan() is True
