import asyncio
from unittest.mock import patch

import pytest

from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.auth import Auth

from .aiohttp import AiohttpClientMocker
from .mock_backendselector import BackendSelectorMock
from .utils import (
    get_mock_coro,
    mock_appliancesmanager_get_account_id_get,
    mock_appliancesmanager_get_owned_appliances_get,
    mock_appliancesmanager_get_shared_appliances_get,
)

BACKEND_SELECTOR_MOCK = BackendSelectorMock()


async def test_create_headers_includes_wp_client_brand(
    http_client_mock: AiohttpClientMocker,
):
    http_client_mock.create_session(asyncio.get_event_loop())
    auth = Auth(BACKEND_SELECTOR_MOCK, "email", "secretpass", http_client_mock.session)
    auth._auth_dict["access_token"] = "acess_token_123"

    am = AppliancesManager(BACKEND_SELECTOR_MOCK, auth, http_client_mock.session)

    headers = am._create_headers()

    assert headers["WP-CLIENT-BRAND"] == BACKEND_SELECTOR_MOCK.brand.name

    await http_client_mock.close_session()


async def test_account_id_set_if_populated_in_auth_dict(
    http_client_mock: AiohttpClientMocker,
):
    http_client_mock.create_session(asyncio.get_event_loop())
    auth = Auth(BACKEND_SELECTOR_MOCK, "email", "secretpass", http_client_mock.session)
    auth._auth_dict["accountId"] = "12345"

    am = AppliancesManager(BACKEND_SELECTOR_MOCK, auth, http_client_mock.session)

    assert am._account_id == "12345"

    await http_client_mock.close_session()


async def test_fetch_appliances_calls_get_account_id_if_not_set(
    http_client_mock: AiohttpClientMocker,
):
    mock_appliancesmanager_get_account_id_get(http_client_mock, BACKEND_SELECTOR_MOCK)

    http_client_mock.create_session(asyncio.get_event_loop())
    auth = Auth(BACKEND_SELECTOR_MOCK, "email", "secretpass", http_client_mock.session)

    am = AppliancesManager(BACKEND_SELECTOR_MOCK, auth, http_client_mock.session)
    am._get_owned_appliances = get_mock_coro(True)
    am._get_shared_appliances = get_mock_coro(False)

    await am.fetch_appliances()

    assert am._account_id == "12345"

    await http_client_mock.close_session()


async def test_fetch_appliances_calls_both_get_methods(
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
    am._get_shared_appliances = get_mock_coro(True)
    am._get_owned_appliances = get_mock_coro(False)

    await am.fetch_appliances()

    am._get_owned_appliances.assert_called()
    am._get_shared_appliances.assert_called()
    await http_client_mock.close_session()


async def test_fetch_appliances_loads_lists(
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

    await am.fetch_appliances()

    assert len(am.washer_dryers) == 2

    await http_client_mock.close_session()


@pytest.mark.parametrize(
    ["owned_response", "shared_response"],
    [(True, True), (True, False), (False, True), (False, False)],
)
async def test_fetch_appliances_returns_false_if_either_method_returns_false(
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

    assert result == bool(owned_response and shared_response)
    await http_client_mock.close_session()
