import asyncio
from http import HTTPStatus

import pytest
from yarl import URL

from whirlpool.auth import Auth

from .aiohttp import AiohttpClientMocker
from .mock_backendselector import BackendSelectorMock

BACKEND_SELECTOR_MOCK = BackendSelectorMock()

AUTH_URL = f"{BACKEND_SELECTOR_MOCK.base_url}/oauth/token"
AUTH_DATA = {
    "client_id": BACKEND_SELECTOR_MOCK.client_id,
    "client_secret": BACKEND_SELECTOR_MOCK.client_secret,
    "grant_type": "password",
    "username": "email",
    "password": "secretpass",
}
AUTH_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
}


pytestmark = pytest.mark.asyncio


async def test_auth_success(http_client_mock: AiohttpClientMocker):
    http_client_mock.create_session(asyncio.get_event_loop())
    auth = Auth(BACKEND_SELECTOR_MOCK, "email", "secretpass", http_client_mock.session)

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
    http_client_mock.post(AUTH_URL, json=mock_resp_data)

    await auth.do_auth(store=False)
    assert auth.is_access_token_valid()
    assert auth.get_said_list() == ["SAID1", "SAID2"]
    assert len(http_client_mock.mock_calls) == 1
    assert http_client_mock.mock_calls[-1][0] == "POST"
    assert http_client_mock.mock_calls[-1][1] == URL(AUTH_URL)
    assert http_client_mock.mock_calls[-1][2] == AUTH_DATA
    assert http_client_mock.mock_calls[-1][3] == AUTH_HEADERS
    await http_client_mock.close_session()


async def test_auth_bad_credentials(http_client_mock: AiohttpClientMocker):
    http_client_mock.create_session(asyncio.get_event_loop())
    auth = Auth(BACKEND_SELECTOR_MOCK, "email", "secretpass", http_client_mock.session)

    mock_resp_data = {
        "error": "invalid_request",
        "error_description": "Bad credentials",
        "code": "13000",
    }
    http_client_mock.post(AUTH_URL, json=mock_resp_data, status=HTTPStatus.BAD_REQUEST)

    await auth.do_auth(store=False)
    assert auth.is_access_token_valid() == False
    assert auth.get_said_list() == None
    assert len(http_client_mock.mock_calls) == 1
    assert http_client_mock.mock_calls[-1][0] == "POST"
    assert http_client_mock.mock_calls[-1][1] == URL(AUTH_URL)
    assert http_client_mock.mock_calls[-1][2] == AUTH_DATA
    assert http_client_mock.mock_calls[-1][3] == AUTH_HEADERS
    await http_client_mock.close_session()
