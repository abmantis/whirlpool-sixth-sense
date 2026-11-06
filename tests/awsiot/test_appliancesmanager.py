"""Tests for AWS IoT appliance routing in AppliancesManager."""

import json
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import aiohttp
import pytest
import pytest_asyncio
from aiointercept import aiointercept

from tests.awsiot.mocks import (
    make_mqtt_factory,
    mock_aws_http_api,
    patch_aws_manager_mqtt,
)
from whirlpool.auth import Auth
from whirlpool.awsiot.appliancesmanager import AppliancesManager as AwsAppliancesManager
from whirlpool.awsiot.appliancesmanager import _is_dryer_model
from whirlpool.awsiot.dryer import Dryer
from whirlpool.awsiot.washer import Washer
from whirlpool.backendselector import BackendSelector

_DATA_DIR = Path(__file__).parent.parent / "data" / "awsiot"

WASHER_THING = json.loads((_DATA_DIR / "washer_thing.json").read_text())
DRYER_THING = json.loads((_DATA_DIR / "dryer_thing.json").read_text())
WASHER_STATE = json.loads((_DATA_DIR / "washer_state.json").read_text())

WASHER_CAP_PART = "W11723751"
DRYER_CAP_PART = "W11729930"


@pytest.mark.parametrize(
    ("model_number", "expected"),
    [
        ("MGD7020RF0", True),  # Maytag gas dryer
        ("MED7020RF0", True),  # Maytag electric dryer
        ("WGD5620HW1", True),  # Whirlpool gas dryer
        ("MFW7020RF0", False),  # Maytag front-load washer
        ("MHW6630HW0", False),  # Maytag front-load washer
        ("WTW5010LW0", False),  # Whirlpool top-load washer
        ("", False),
        ("MF", False),
    ],
)
def test_is_dryer_model(model_number: str, expected: bool) -> None:
    assert _is_dryer_model(model_number) is expected


@pytest_asyncio.fixture
async def laundry_manager(
    auth: Auth,
    backend_selector: BackendSelector,
    client_session_fixture: aiohttp.ClientSession,
    aiointercept_mock: aiointercept,
) -> AsyncGenerator[AwsAppliancesManager]:
    """An AwsAppliancesManager connected to a washer + dryer thing."""

    mock_aws_http_api(aiointercept_mock, backend_selector, [WASHER_THING, DRYER_THING])
    capability_replies: dict[str, dict[str, Any] | None] = {
        WASHER_CAP_PART: {"partNumber": WASHER_CAP_PART},
        DRYER_CAP_PART: {"partNumber": DRYER_CAP_PART},
    }
    mqtt_factory = make_mqtt_factory(WASHER_STATE, capability_replies)
    with patch_aws_manager_mqtt(mqtt_factory):
        manager = AwsAppliancesManager(auth, client_session_fixture, lambda: None)
        ok = await manager.connect()
        assert ok is True
        yield manager


async def test_laundry_category_is_split_into_washer_and_dryer(
    laundry_manager: AwsAppliancesManager,
) -> None:
    assert len(laundry_manager.washers) == 1
    assert len(laundry_manager.dryers) == 1

    washer = laundry_manager.washers[0]
    dryer = laundry_manager.dryers[0]

    assert isinstance(washer, Washer)
    assert isinstance(dryer, Dryer)
    assert washer.said == "WPR1W00000001"
    assert dryer.said == "WPR1D00000002"


async def test_laundry_fixtures_surface_standby_state(
    laundry_manager: AwsAppliancesManager,
) -> None:
    washer = laundry_manager.washers[0]
    assert washer.get_machine_state() is not None
    assert washer.get_time_remaining() == 5351
