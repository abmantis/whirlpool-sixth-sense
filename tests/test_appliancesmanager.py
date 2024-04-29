import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from yarl import URL

from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.auth import Auth
from whirlpool.backendselector import BackendSelector

CURR_DIR = Path(__file__).parent
DATA_DIR = CURR_DIR / "data"
ACCOUNT_ID = "12345"


def get_mock_coro(return_value):
    async def mock_coro(*args, **kwargs):
        return return_value

    return Mock(wraps=mock_coro)


with open(DATA_DIR / "owned_appliances.json") as f:
    owned_appliance_data = json.load(f)

with open(DATA_DIR / "shared_appliances.json") as f:
    shared_appliance_data = json.load(f)


@pytest.fixture(autouse=True)
def account_id_calls_fixture(aioresponses_mock, backend_selector_mock):
    """Mock the calls to get the user details and owned appliances.

    This is required by all of the tests in this file, so we use the autouse=True
    parameter to ensure that this fixture is always run.
    """
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
    yield


async def test_uer_details_not_called_if_account_id_is_known(
    auth_mock: Auth,
    backend_selector_mock: BackendSelector,
    appliances_manager: AppliancesManager,
    aioresponses_mock,
):
    auth_mock._auth_dict["accountId"] = ACCOUNT_ID

    await appliances_manager.fetch_appliances()

    assert (
        "GET",
        URL(backend_selector_mock.user_details_url),
    ) not in aioresponses_mock.requests


async def test_user_details_called_if_account_id_not_known(
    backend_selector_mock: BackendSelector,
    appliances_manager: AppliancesManager,
    aioresponses_mock,
):
    await appliances_manager.fetch_appliances()

    aioresponses_mock.assert_any_call(
        URL(backend_selector_mock.user_details_url), "GET"
    )


async def test_get_owned_appliances_call_does_not_contain_wp_client_brand_header(
    backend_selector_mock: BackendSelector,
    appliances_manager: AppliancesManager,
    aioresponses_mock,
):
    await appliances_manager.fetch_appliances()

    # call to get owned appliances - this one cannot contain the WP-CLIENT-BRAND header
    owned_call = aioresponses_mock.requests[
        ("GET", URL(backend_selector_mock.get_owned_appliances_url(ACCOUNT_ID)))
    ]
    assert len(owned_call) == 1
    owned_call_headers = owned_call[0][1]["headers"]
    assert "WP-CLIENT-BRAND" not in owned_call_headers


async def test_get_shared_appliances_call_contains_wp_client_brand_header(
    backend_selector_mock: BackendSelector,
    appliances_manager: AppliancesManager,
    aioresponses_mock,
):
    await appliances_manager.fetch_appliances()

    # call to get shared appliances - this one should contain the WP-CLIENT-BRAND header
    shared_call = aioresponses_mock.requests[
        ("GET", URL(backend_selector_mock.shared_appliances_url))
    ]
    assert len(shared_call) == 1
    shared_call_headers = shared_call[0][1]["headers"]
    assert shared_call_headers["WP-CLIENT-BRAND"] == "DUMMY_BRAND"


async def test_fetch_appliances_returns_owned_and_shared_appliances(
    appliances_manager: AppliancesManager,
):
    await appliances_manager.fetch_appliances()

    # the test data has one owned appliance and one shared appliance
    # so if this is 2 then we have both
    assert len(appliances_manager.washer_dryers) == 2


async def test_fetch_appliances_calls_owned_and_shared_methods(
    appliances_manager: AppliancesManager,
):
    shared_appliance_mock = get_mock_coro(None)
    owned_appliance_mock = get_mock_coro(None)

    appliances_manager._get_shared_appliances = shared_appliance_mock
    appliances_manager._get_owned_appliances = owned_appliance_mock

    await appliances_manager.fetch_appliances()

    assert shared_appliance_mock.called
    assert owned_appliance_mock.called


@pytest.mark.parametrize(
    ["owned_response", "shared_response"],
    [(True, True), (True, False), (False, True), (False, False)],
)
async def test_fetch_appliances_returns_true_if_either_method_returns_true(
    owned_response: bool, shared_response: bool, appliances_manager: AppliancesManager
):
    appliances_manager._get_shared_appliances = get_mock_coro(shared_response)
    appliances_manager._get_owned_appliances = get_mock_coro(owned_response)

    result = await appliances_manager.fetch_appliances()

    assert result == bool(owned_response or shared_response)
