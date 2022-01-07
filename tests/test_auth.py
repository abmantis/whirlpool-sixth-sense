import json
import logging
import pytest
from tests.mock_backendselector import BackendSelectorMock

from whirlpool.auth import Auth

from . import MockResponse

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


async def test_auth_success(caplog, aio_httpclient):
    caplog.set_level(logging.DEBUG)
    auth = Auth(BACKEND_SELECTOR_MOCK, "email", "secretpass")

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
    aio_httpclient.post.return_value = MockResponse(json.dumps(mock_resp_data), 200)

    await auth.do_auth(store=False)
    assert auth.is_access_token_valid()
    assert auth.get_said_list() == ["SAID1", "SAID2"]
    aio_httpclient.post.assert_called_with(
        AUTH_URL, data=AUTH_DATA, headers=AUTH_HEADERS
    )
    aio_httpclient.close.assert_called_once()


async def test_auth_bad_credentials(caplog, aio_httpclient):
    caplog.set_level(logging.DEBUG)
    auth = Auth(BACKEND_SELECTOR_MOCK, "email", "secretpass")

    mock_resp_data = {
        "error": "invalid_request",
        "error_description": "Bad credentials",
        "code": "13000",
    }
    aio_httpclient.post.return_value = MockResponse(json.dumps(mock_resp_data), 400)

    await auth.do_auth(store=False)
    assert auth.is_access_token_valid() == False
    assert auth.get_said_list() == None
    aio_httpclient.post.assert_called_with(
        AUTH_URL, data=AUTH_DATA, headers=AUTH_HEADERS
    )
    aio_httpclient.close.assert_called_once()
