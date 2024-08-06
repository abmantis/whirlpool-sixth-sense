import json
from pathlib import Path

import pytest

from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.backendselector import BackendSelector

CURR_DIR = Path(__file__).parent
DATA_DIR = CURR_DIR / "data"
ACCOUNT_ID = "12345"
HEADERS = {
    "Authorization": "Bearer None",
    "Content-Type": "application/json",
    "User-Agent": "okhttp/3.12.0",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
}


@pytest.fixture(autouse=True)
def common_http_calls_fixture(aioresponses_mock, backend_selector_mock):
    """Mock the calls to get the user details and owned appliances.

    This is required by all of the tests in this file, so we use the autouse=True
    parameter to ensure that this fixture is always run.
    """
    with open(DATA_DIR / "owned_appliances.json") as f:
        owned_appliance_data = json.load(f)

    with open(DATA_DIR / "shared_appliances.json") as f:
        shared_appliance_data = json.load(f)

    aioresponses_mock.get(
        backend_selector_mock.user_details_url, payload={"accountId": ACCOUNT_ID}
    )
    aioresponses_mock.get(
        backend_selector_mock.get_owned_appliances_url(ACCOUNT_ID),
        payload={ACCOUNT_ID: owned_appliance_data},
    )
    aioresponses_mock.get(
        backend_selector_mock.shared_appliances_url, payload=shared_appliance_data
    )


async def test_fetch_appliances_returns_owned_and_shared_appliances(
    appliances_manager: AppliancesManager,
):
    await appliances_manager.fetch_appliances()

    # the test data has one owned appliance and one shared appliance
    # so if this is 2 then we have both
    assert len(appliances_manager.washer_dryers) == 2

    # ensure oven list is populated
    assert len(appliances_manager.ovens) == 1


async def test_fetch_appliances_calls_owned_and_shared_methods(
    appliances_manager: AppliancesManager,
    backend_selector_mock: BackendSelector,
    aioresponses_mock,
):
    shared_headers = {**HEADERS, "WP-CLIENT-BRAND": backend_selector_mock.brand.name}

    await appliances_manager.fetch_appliances()

    aioresponses_mock.assert_called_with(
        backend_selector_mock.get_owned_appliances_url(ACCOUNT_ID),
        "GET",
        headers=HEADERS,
    )

    aioresponses_mock.assert_called_with(
        backend_selector_mock.shared_appliances_url, "GET", headers=shared_headers
    )
