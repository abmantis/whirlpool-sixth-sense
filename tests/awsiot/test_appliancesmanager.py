"""Tests for AWS IoT laundry routing in AppliancesManager.

The laundry fixtures are a Maytag MTW7205RR0 top-load washer and MGD7205RR0
dryer captured as-is (thing, full capability file and state), from
https://github.com/abmantis/whirlpool-sixth-sense/issues/117.
"""

import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import aiohttp
import pytest
from aiointercept import aiointercept

from tests.awsiot.mocks import (
    make_mqtt_factory,
    mock_aws_http_api,
    patch_aws_manager_mqtt,
)
from whirlpool.auth import Auth
from whirlpool.awsiot.appliancesmanager import AppliancesManager as AwsAppliancesManager
from whirlpool.awsiot.dryer import Dryer
from whirlpool.awsiot.washer import Washer
from whirlpool.backendselector import BackendSelector
from whirlpool.dryer import MachineState as DryerMachineState
from whirlpool.washer import MachineState as WasherMachineState

_DATA_DIR = Path(__file__).parent.parent / "data" / "awsiot"


def _load(name: str) -> dict[str, Any]:
    return json.loads((_DATA_DIR / name).read_text())


WASHER_THING = _load("washer_MTW7205RR0_thing.json")
WASHER_STATE = _load("washer_MTW7205RR0_state.json")
WASHER_CAPABILITY = _load("capability_washer_W11771387.json")
DRYER_THING = _load("dryer_MGD7205RR0_thing.json")
DRYER_STATE = _load("dryer_MGD7205RR0_state.json")
DRYER_CAPABILITY = _load("capability_dryer_W11771436.json")

WASHER_SAID = WASHER_THING["thingName"]
DRYER_SAID = DRYER_THING["thingName"]
WASHER_CAP_PART = "W11771387"
DRYER_CAP_PART = "W11771436"

# A Canadian electric dryer, captured from a real account. Its thingTypeName
# keeps the "Y" prefix, so the third character is "E", which the old
# model-number heuristic read as a washer.
Y_DRYER_THING = _load("dryer_YMED7205RF0_thing.json")
Y_DRYER_STATE = _load("dryer_YMED7205RF0_state.json")
Y_DRYER_SAID = Y_DRYER_THING["thingName"]

type ConnectLaundry = Callable[
    [list[dict[str, Any]], dict[str, dict[str, Any] | None]],
    Awaitable[AwsAppliancesManager],
]


@pytest.fixture
def connect_laundry(
    auth: Auth,
    backend_selector: BackendSelector,
    client_session_fixture: aiohttp.ClientSession,
    aiointercept_mock: aiointercept,
) -> ConnectLaundry:
    """Connect a manager over `things`, answering capability requests by part.

    Each SAID gets its own captured state on getState.
    """

    async def _connect(
        things: list[dict[str, Any]],
        capability_replies: dict[str, dict[str, Any] | None],
    ) -> AwsAppliancesManager:
        mock_aws_http_api(aiointercept_mock, backend_selector, things)
        mqtt_factory = make_mqtt_factory(
            None,
            capability_replies,
            getstate_replies_by_said={
                WASHER_SAID: WASHER_STATE,
                DRYER_SAID: DRYER_STATE,
                Y_DRYER_SAID: Y_DRYER_STATE,
            },
        )
        with patch_aws_manager_mqtt(mqtt_factory):
            manager = AwsAppliancesManager(auth, client_session_fixture, lambda: None)
            assert await manager.connect() is True
        return manager

    return _connect


def _dryer_thing(model: str, category: str, cap_part: str) -> dict[str, Any]:
    """The captured dryer thing with its model, category and part replaced."""
    return {
        **DRYER_THING,
        "thingTypeName": model,
        "attributes": {
            **DRYER_THING["attributes"],
            "Category": category,
            "CapabilityPartNumber": cap_part,
        },
    }


async def test_laundry_category_is_split_by_declared_cavity(
    connect_laundry: ConnectLaundry,
) -> None:
    manager = await connect_laundry(
        [WASHER_THING, DRYER_THING],
        {WASHER_CAP_PART: WASHER_CAPABILITY, DRYER_CAP_PART: DRYER_CAPABILITY},
    )
    assert len(manager.washers) == 1
    assert len(manager.dryers) == 1

    washer = manager.washers[0]
    dryer = manager.dryers[0]

    assert isinstance(washer, Washer)
    assert washer.said == WASHER_SAID
    assert washer.capability_profile.cavity == "washer"
    assert washer.capability_profile.part_number == WASHER_CAP_PART

    assert isinstance(dryer, Dryer)
    assert dryer.said == DRYER_SAID
    assert dryer.capability_profile.cavity == "dryer"
    assert dryer.capability_profile.part_number == DRYER_CAP_PART


async def test_each_laundry_appliance_reads_its_own_state(
    connect_laundry: ConnectLaundry,
) -> None:
    manager = await connect_laundry(
        [WASHER_THING, DRYER_THING],
        {WASHER_CAP_PART: WASHER_CAPABILITY, DRYER_CAP_PART: DRYER_CAPABILITY},
    )
    washer = manager.washers[0]
    dryer = manager.dryers[0]

    assert washer.get_machine_state() is WasherMachineState.Standby
    # The top-load capture reports doorStatus "open".
    assert washer.get_door_open() is True
    assert dryer.get_machine_state() is DryerMachineState.Standby
    assert dryer.get_door_open() is False


async def test_laundry_without_a_cavity_is_skipped(
    connect_laundry: ConnectLaundry, caplog: pytest.LogCaptureFixture
) -> None:
    thing = _dryer_thing(Y_DRYER_THING["thingTypeName"], "Laundry", "W0")
    manager = await connect_laundry([thing], {"W0": {"partNumber": "W0"}})

    assert manager.washers == []
    assert manager.dryers == []
    # The warning names the appliance and the file, not just an unknown category.
    assert any(
        record.levelname == "WARNING"
        and DRYER_SAID in record.getMessage()
        and "skipped" in record.getMessage()
        and "W0" in record.getMessage()
        for record in caplog.records
    )


async def test_y_prefixed_model_routes_by_declared_cavity(
    connect_laundry: ConnectLaundry,
) -> None:
    assert Y_DRYER_THING["thingTypeName"] == "YMED7205RF0"
    assert Y_DRYER_THING["attributes"]["CapabilityPartNumber"] == DRYER_CAP_PART
    manager = await connect_laundry([Y_DRYER_THING], {DRYER_CAP_PART: DRYER_CAPABILITY})

    assert manager.washers == []
    assert len(manager.dryers) == 1
    dryer = manager.dryers[0]
    assert isinstance(dryer, Dryer)
    assert dryer.said == Y_DRYER_SAID
    assert dryer.capability_profile.cavity == "dryer"
    assert dryer.get_machine_state() is DryerMachineState.Standby


async def test_fabriccare_category_is_not_routed(
    connect_laundry: ConnectLaundry,
) -> None:
    # "FabricCare" is the HTTP backend's category name; no AWS thing has
    # reported it.
    thing = _dryer_thing(DRYER_THING["thingTypeName"], "FabricCare", DRYER_CAP_PART)
    manager = await connect_laundry([thing], {DRYER_CAP_PART: DRYER_CAPABILITY})

    assert manager.all_appliances == {}


async def test_capability_declaring_both_cavities_is_skipped(
    connect_laundry: ConnectLaundry, caplog: pytest.LogCaptureFixture
) -> None:
    both = {"partNumber": "X", "cavities": {"washer": {}, "dryer": {}}}
    thing = _dryer_thing(DRYER_THING["thingTypeName"], "Laundry", "X")
    manager = await connect_laundry([thing], {"X": both})

    assert manager.all_appliances == {}
    assert any(
        record.levelname == "WARNING"
        and DRYER_SAID in record.getMessage()
        and "['dryer', 'washer']" in record.getMessage()
        for record in caplog.records
    )
