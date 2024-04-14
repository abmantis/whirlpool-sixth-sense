import json
from pathlib import Path
from unittest.mock import Mock

import aiohttp
import pytest
from aioresponses import aioresponses
from yarl import URL

from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.auth import Auth

from .mock_backendselector import BackendSelectorMock

BACKEND_SELECTOR_MOCK = BackendSelectorMock()

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


@pytest.mark.parametrize("account_id", [None, ACCOUNT_ID])
async def test_fetch_appliances_with_set_account_id(account_id: str):
    session = aiohttp.ClientSession()
    auth = Auth(BACKEND_SELECTOR_MOCK, "email", "secretpass", session)

    with aioresponses() as m:
        m.get(BACKEND_SELECTOR_MOCK.user_details_url, payload={"accountId": "12345"})
        m.get(
            BACKEND_SELECTOR_MOCK.get_owned_appliances_url(ACCOUNT_ID),
            payload={ACCOUNT_ID: owned_appliance_data},
        )
        m.get(
            BACKEND_SELECTOR_MOCK.shared_appliances_url, payload=shared_appliance_data
        )

        if account_id is not None:
            auth._auth_dict["accountId"] = account_id

        am = AppliancesManager(BACKEND_SELECTOR_MOCK, auth, session)

        await am.fetch_appliances()

        if account_id is None:
            m.assert_any_call(URL(BACKEND_SELECTOR_MOCK.user_details_url), "GET")
        else:
            assert (
                "GET",
                URL(BACKEND_SELECTOR_MOCK.user_details_url),
            ) not in m.requests

        # call to get owned appliances - this one cannot contain the WP-CLIENT-BRAND header
        owned_call = m.requests[
            ("GET", URL(BACKEND_SELECTOR_MOCK.get_owned_appliances_url(ACCOUNT_ID)))
        ]
        assert len(owned_call) == 1
        owned_call_headers = owned_call[0][1]["headers"]
        assert "WP-CLIENT-BRAND" not in owned_call_headers

        # call to get shared appliances - this one should contain the WP-CLIENT-BRAND header
        shared_call = m.requests[
            ("GET", URL(BACKEND_SELECTOR_MOCK.shared_appliances_url))
        ]
        assert len(shared_call) == 1
        shared_call_headers = shared_call[0][1]["headers"]
        assert shared_call_headers["WP-CLIENT-BRAND"] == "DUMMY_BRAND"

        # ensure that the washer_dryers list is populated
        assert len(am.washer_dryers) == 2

        await session.close()


@pytest.mark.parametrize(
    ["owned_response", "shared_response"],
    [(True, True), (True, False), (False, True), (False, False)],
)
async def test_fetch_appliances_returns_true_if_either_method_returns_true(
    owned_response: bool, shared_response: bool
):
    session = aiohttp.ClientSession()
    auth = Auth(BACKEND_SELECTOR_MOCK, "email", "secretpass", session)

    with aioresponses() as m:
        m.get(BACKEND_SELECTOR_MOCK.user_details_url, payload={"accountId": "12345"})
        m.get(
            BACKEND_SELECTOR_MOCK.get_owned_appliances_url(ACCOUNT_ID),
            payload={ACCOUNT_ID: owned_appliance_data},
        )
        m.get(
            BACKEND_SELECTOR_MOCK.shared_appliances_url, payload=shared_appliance_data
        )

        auth = Auth(BACKEND_SELECTOR_MOCK, "email", "secretpass", session)

        am = AppliancesManager(BACKEND_SELECTOR_MOCK, auth, session)
        am._get_shared_appliances = get_mock_coro(shared_response)
        am._get_owned_appliances = get_mock_coro(owned_response)

        result = await am.fetch_appliances()

        assert result == bool(owned_response or shared_response)
    await session.close()
