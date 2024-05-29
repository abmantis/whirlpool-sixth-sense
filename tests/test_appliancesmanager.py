import asyncio

import pytest

from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.auth import Auth

from .aiohttp import AiohttpClientMocker
from .mock_backendselector import BackendSelectorMock
from .utils import (
    ACCOUNT_ID,
    get_mock_coro,
    mock_appliancesmanager_get_account_id_get,
    mock_appliancesmanager_get_owned_appliances_get,
    mock_appliancesmanager_get_shared_appliances_get,
)

BACKEND_SELECTOR_MOCK = BackendSelectorMock()


def assert_appliances_manager_call(
    http_client_mock: AiohttpClientMocker,
    call_index: int,
    path: str,
    required_headers: dict = None,
    forbidden_headers: list = None,
):
    mock_calls = http_client_mock.mock_calls

    call = mock_calls[call_index]
    assert call[0] == "GET"
    assert BACKEND_SELECTOR_MOCK.base_url + call[1].path == path
    # call[2] is body, which will be None

    if required_headers is not None:
        for k, v in required_headers.items():
            assert call[3][k] == v

    if forbidden_headers is not None:
        for k in forbidden_headers:
            assert k not in call[3]


@pytest.mark.parametrize("account_id", [None, ACCOUNT_ID])
async def test_fetch_appliances_with_set_account_id(
    account_id: str, http_client_mock: AiohttpClientMocker
):
    get_appliances_idx = 0 if account_id is not None else 1

    mock_appliancesmanager_get_account_id_get(http_client_mock, BACKEND_SELECTOR_MOCK)
    mock_appliancesmanager_get_owned_appliances_get(
        http_client_mock, BACKEND_SELECTOR_MOCK, ACCOUNT_ID
    )
    mock_appliancesmanager_get_shared_appliances_get(
        http_client_mock, BACKEND_SELECTOR_MOCK
    )

    http_client_mock.create_session(asyncio.get_event_loop())
    auth = Auth(BACKEND_SELECTOR_MOCK, "email", "secretpass", http_client_mock.session)

    if account_id is not None:
        auth._auth_dict["accountId"] = account_id

    am = AppliancesManager(BACKEND_SELECTOR_MOCK, auth, http_client_mock.session)

    await am.fetch_appliances()

    if account_id is None:
        # make sure that the first call in this case is to get the account id
        assert_appliances_manager_call(
            http_client_mock, 0, BACKEND_SELECTOR_MOCK.user_details_url
        )

    # this should always be called
    assert_appliances_manager_call(
        http_client_mock,
        get_appliances_idx,
        BACKEND_SELECTOR_MOCK.get_owned_appliances_url(ACCOUNT_ID),
        forbidden_headers=["WP-CLIENT-BRAND"],
    )

    # this should always be called and requires the WP-CLIENT-BRAND header
    assert_appliances_manager_call(
        http_client_mock,
        get_appliances_idx + 1,
        BACKEND_SELECTOR_MOCK.shared_appliances_url,
        {"WP-CLIENT-BRAND": "DUMMY_BRAND"},
    )

    # ensure that the washer_dryers list is populated
    assert len(am.washer_dryers) == 2
    # ensure that the oven list is populated
    assert len(am.ovens) == 1

    await http_client_mock.close_session()


@pytest.mark.parametrize(
    ["owned_response", "shared_response"],
    [(True, True), (True, False), (False, True), (False, False)],
)
async def test_fetch_appliances_returns_true_if_either_method_returns_true(
    owned_response: bool,
    shared_response: bool,
    http_client_mock: AiohttpClientMocker,
):
    mock_appliancesmanager_get_account_id_get(http_client_mock, BACKEND_SELECTOR_MOCK)
    mock_appliancesmanager_get_owned_appliances_get(
        http_client_mock, BACKEND_SELECTOR_MOCK, "12345"
    )
    mock_appliancesmanager_get_shared_appliances_get(
        http_client_mock, BACKEND_SELECTOR_MOCK
    )

    http_client_mock.create_session(asyncio.get_event_loop())
    auth = Auth(BACKEND_SELECTOR_MOCK, "email", "secretpass", http_client_mock.session)

    am = AppliancesManager(BACKEND_SELECTOR_MOCK, auth, http_client_mock.session)
    am._get_shared_appliances = get_mock_coro(shared_response)
    am._get_owned_appliances = get_mock_coro(owned_response)

    result = await am.fetch_appliances()

    assert result == bool(owned_response or shared_response)
    await http_client_mock.close_session()
