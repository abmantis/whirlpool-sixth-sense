import asyncio
from http import HTTPStatus

import pytest
from yarl import URL

from whirlpool.auth import Auth

from .aiohttp import AiohttpClientMocker
from .mock_backendselector import BackendSelectorMock, BackendSelectorMockMultipleCreds

AUTH_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
}

BACKEND_SELECTORS = [BackendSelectorMockMultipleCreds(), BackendSelectorMock()]

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize("refresh_token", [None, "refresh_token_123"])
@pytest.mark.parametrize("backend_selector", BACKEND_SELECTORS)
async def test_get_auth_body(
    backend_selector, refresh_token, http_client_mock: AiohttpClientMocker
):
    http_client_mock.create_session(asyncio.get_event_loop())
    auth = Auth(
        backend_selector=backend_selector,
        username="email",
        password="secretpass",
        session=http_client_mock.session,
    )
    for cred in backend_selector.client_credentials:
        auth_data = auth._get_auth_body(refresh_token, cred)

        assert auth_data["client_id"] == cred["client_id"]
        assert auth_data["client_secret"] == cred["client_secret"]

        if not refresh_token:
            assert auth_data["grant_type"] == "password"
            assert auth_data["username"] == "email"
            assert auth_data["password"] == "secretpass"

        if refresh_token:
            assert auth_data["grant_type"] == "refresh_token"
            assert auth_data["refresh_token"] == refresh_token

    await http_client_mock.close_session()


@pytest.mark.parametrize("backend_selector", BACKEND_SELECTORS)
async def test_auth_success(backend_selector, http_client_mock: AiohttpClientMocker):
    http_client_mock.create_session(asyncio.get_event_loop())
    auth = Auth(backend_selector, "email", "secretpass", http_client_mock.session)

    mock_resp_data = {
        "access_token": "acess_token_123",
        "token_type": "bearer",
        "refresh_token": "refresher_123",
        "expires_in": 21599,
        "scope": "trust read write",
        "accountId": 12345,
        "SAID": ["SAID1", "SAID2"],
        "jti": "?????",
    }
    http_client_mock.post(backend_selector.auth_url, json=mock_resp_data)

    await auth.do_auth(store=False)
    assert auth.is_access_token_valid()
    assert auth.get_said_list() == ["SAID1", "SAID2"]
    assert http_client_mock.mock_calls[-1][0] == "POST"
    assert http_client_mock.mock_calls[-1][1] == URL(backend_selector.auth_url)
    assert http_client_mock.mock_calls[-1][3] == AUTH_HEADERS
    await http_client_mock.close_session()


@pytest.mark.parametrize("backend_selector", BACKEND_SELECTORS)
async def test_auth_bad_credentials(
    backend_selector, http_client_mock: AiohttpClientMocker
):
    http_client_mock.create_session(asyncio.get_event_loop())
    auth = Auth(backend_selector, "email", "secretpass", http_client_mock.session)

    mock_resp_data = {
        "error": "invalid_request",
        "error_description": "Bad credentials",
        "code": "13000",
    }
    http_client_mock.post(
        backend_selector.auth_url, json=mock_resp_data, status=HTTPStatus.BAD_REQUEST
    )

    await auth.do_auth(store=False)
    assert auth.is_access_token_valid() is False
    assert auth.get_said_list() is None
    assert http_client_mock.mock_calls[-1][0] == "POST"
    assert http_client_mock.mock_calls[-1][1] == URL(backend_selector.auth_url)
    assert http_client_mock.mock_calls[-1][3] == AUTH_HEADERS
    await http_client_mock.close_session()
