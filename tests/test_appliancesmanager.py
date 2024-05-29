import json
from pathlib import Path

import pytest

from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.backendselector import BackendSelector

CURR_DIR = Path(__file__).parent
DATA_DIR = CURR_DIR / "data"
ACCOUNT_ID = "12345"


@pytest.fixture(autouse=True)
def account_id_calls_fixture(aioresponses_mock, backend_selector_mock):
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


async def test_get_owned_appliances_call_does_not_contain_wp_client_brand_header(
    backend_selector_mock: BackendSelector,
    appliances_manager: AppliancesManager,
    aioresponses_mock,
):
    await appliances_manager.fetch_appliances()

    headers = appliances_manager._create_headers()

    aioresponses_mock.assert_called_with(
        backend_selector_mock.get_owned_appliances_url(ACCOUNT_ID),
        "GET",
        headers=headers,
    )

    assert "WP-CLIENT-BRAND" not in headers


async def test_get_shared_appliances_call_contains_wp_client_brand_header(
    backend_selector_mock: BackendSelector,
    appliances_manager: AppliancesManager,
    aioresponses_mock,
):
    await appliances_manager.fetch_appliances()

    headers = appliances_manager._create_headers(include_wp_brand_name=True)

    aioresponses_mock.assert_called_with(
        backend_selector_mock.shared_appliances_url, "GET", headers=headers
    )

    assert headers["WP-CLIENT-BRAND"] == backend_selector_mock.brand.name


async def test_fetch_appliances_returns_owned_and_shared_appliances(
    appliances_manager: AppliancesManager,
):
    await appliances_manager.fetch_appliances()

    # the test data has one owned appliance and one shared appliance
    # so if this is 2 then we have both
    assert len(appliances_manager.washer_dryers) == 2


async def test_fetch_appliances_calls_owned_and_shared_methods(
    appliances_manager: AppliancesManager,
    backend_selector_mock: BackendSelector,
    aioresponses_mock,
):
    owned_headers = appliances_manager._create_headers()
    shared_headers = appliances_manager._create_headers(include_wp_brand_name=True)

    await appliances_manager.fetch_appliances()

    aioresponses_mock.assert_called_with(
        backend_selector_mock.get_owned_appliances_url(ACCOUNT_ID),
        "GET",
        headers=owned_headers,
    )

    aioresponses_mock.assert_called_with(
        backend_selector_mock.shared_appliances_url, "GET", headers=shared_headers
    )
