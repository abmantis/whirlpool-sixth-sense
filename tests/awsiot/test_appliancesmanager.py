"""Tests for AWS IoT laundry routing in AppliancesManager."""

import json
from collections.abc import AsyncGenerator, Awaitable, Callable
from pathlib import Path
from typing import Any

import aiohttp
import pytest
import pytest_asyncio
from aiointercept import aiointercept

from tests.awsiot.mocks import FakePahoBroker, mock_aws_http_api
from whirlpool.auth import Auth
from whirlpool.awsiot.appliancesmanager import AppliancesManager as AwsAppliancesManager
from whirlpool.awsiot.washer import Washer
from whirlpool.backendselector import BackendSelector
from whirlpool.washer import MachineState

_DATA_DIR = Path(__file__).parent.parent / "data" / "awsiot"


def _load(name: str) -> dict[str, Any]:
    return json.loads((_DATA_DIR / name).read_text())


# An MTW7205RR0 top-load: thing, capability file and state as captured.
WASHER_THING = _load("washer_MTW7205RR0_thing.json")
WASHER_STATE = _load("washer_MTW7205RR0_state.json")
WASHER_CAPABILITY = _load("capability_washer_W11771387.json")
WASHER_SAID = WASHER_THING["thingName"]
WASHER_CAP_PART = "W11771387"

type ConnectLaundry = Callable[
    [list[dict[str, Any]], dict[str, dict[str, Any] | None]],
    Awaitable[AwsAppliancesManager],
]


@pytest_asyncio.fixture
async def connect_laundry(
    auth: Auth,
    backend_selector: BackendSelector,
    client_session_fixture: aiohttp.ClientSession,
    aiointercept_mock: aiointercept,
    fake_paho_broker: FakePahoBroker,
) -> AsyncGenerator[ConnectLaundry]:
    """Connect a manager over `things`, each replying with the washer state."""
    managers: list[AwsAppliancesManager] = []

    async def _connect(
        things: list[dict[str, Any]],
        capabilities: dict[str, dict[str, Any] | None],
    ) -> AwsAppliancesManager:
        mock_aws_http_api(aiointercept_mock, backend_selector, things)
        for thing in things:
            fake_paho_broker.states[thing["thingName"]] = WASHER_STATE
        fake_paho_broker.capabilities.update(capabilities)
        manager = AwsAppliancesManager(auth, client_session_fixture, lambda: None)
        assert await manager.connect() is True
        managers.append(manager)
        return manager

    yield _connect
    for manager in managers:
        await manager.disconnect()


def _laundry_thing(category: str, cap_part: str) -> dict[str, Any]:
    return {
        **WASHER_THING,
        "attributes": {
            **WASHER_THING["attributes"],
            "Category": category,
            "CapabilityPartNumber": cap_part,
        },
    }


def _skip_warning(caplog: pytest.LogCaptureFixture, *words: str) -> bool:
    return any(
        record.levelname == "WARNING"
        and WASHER_SAID in record.getMessage()
        and "skipped" in record.getMessage()
        and all(word in record.getMessage() for word in words)
        for record in caplog.records
    )


async def test_washer_cavity_routes_to_washer(
    connect_laundry: ConnectLaundry,
) -> None:
    manager = await connect_laundry(
        [WASHER_THING], {WASHER_CAP_PART: WASHER_CAPABILITY}
    )
    assert manager.dryers == []
    (washer,) = manager.washers
    assert isinstance(washer, Washer)
    assert washer.said == WASHER_SAID
    assert washer.capability_profile.cavity == "washer"
    assert washer.capability_profile.part_number == WASHER_CAP_PART


async def test_washer_reads_its_state(connect_laundry: ConnectLaundry) -> None:
    manager = await connect_laundry(
        [WASHER_THING], {WASHER_CAP_PART: WASHER_CAPABILITY}
    )
    (washer,) = manager.washers
    assert washer.get_machine_state() is MachineState.Standby
    assert washer.get_door_open() is True


@pytest.mark.parametrize(
    ("cavities", "named"),
    [
        pytest.param({}, "[]", id="none"),
        pytest.param({"dryer": {}}, "['dryer']", id="dryer"),
        pytest.param({"washer": {}, "dryer": {}}, "['dryer', 'washer']", id="both"),
    ],
)
async def test_laundry_without_a_washer_alone_is_skipped(
    connect_laundry: ConnectLaundry,
    caplog: pytest.LogCaptureFixture,
    cavities: dict[str, Any],
    named: str,
) -> None:
    thing = _laundry_thing("Laundry", "X")
    manager = await connect_laundry(
        [thing], {"X": {"partNumber": "X", "cavities": cavities}}
    )
    assert manager.all_appliances == {}
    assert _skip_warning(caplog, "X", named)


async def test_fabriccare_category_is_not_routed(
    connect_laundry: ConnectLaundry,
) -> None:
    # The HTTP backend's category name; no AWS thing has reported it.
    thing = _laundry_thing("FabricCare", WASHER_CAP_PART)
    manager = await connect_laundry([thing], {WASHER_CAP_PART: WASHER_CAPABILITY})
    assert manager.all_appliances == {}
