from http import HTTPStatus

import aiohttp
import pytest
from aioresponses import aioresponses
from yarl import URL

from whirlpool.auth import Auth

from .mock_backendselector import BackendSelectorMock, BackendSelectorMockMultipleCreds

BACKEND_SELECTOR_MOCK = BackendSelectorMock()
BACKEND_SELECTOR_MOCK_MULTIPLE_CREDS = BackendSelectorMockMultipleCreds()

AUTH_URL = f"{BACKEND_SELECTOR_MOCK.base_url}/oauth/token"
AUTH_DATA = {
    "client_id": BACKEND_SELECTOR_MOCK.client_credentials[0]["client_id"],
    "client_secret": BACKEND_SELECTOR_MOCK.client_credentials[0]["client_secret"],
    "grant_type": "password",
    "username": "email",
    "password": "secretpass",
}
AUTH_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "okhttp/3.12.0",
}


pytestmark = pytest.mark.asyncio


async def test_auth_success():
    session = aiohttp.ClientSession()
    auth = Auth(BACKEND_SELECTOR_MOCK, "email", "secretpass", session)

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
    with aioresponses() as m:
        m.post(AUTH_URL, payload=mock_resp_data)

        await auth.do_auth(store=False)
        assert auth.is_access_token_valid()
        assert auth.get_said_list() == ["SAID1", "SAID2"]

        # assert that the proper method and url were used
        assert ("POST", URL(AUTH_URL)) in m.requests

        # get the calls for the method/url and assert length
        calls = m.requests[("POST", URL(AUTH_URL))]
        assert len(calls) == 1

        # actual call, as a tuple
        call = calls[0]
        assert call[1]["data"] == AUTH_DATA
        assert call[1]["headers"] == AUTH_HEADERS
        await session.close()


async def test_auth_multiple_client_credentials(caplog):
    # need to capture at debug level to get status - we don't return status or have any
    # other good way to check it
    caplog.set_level("DEBUG")

    session = aiohttp.ClientSession()
    auth = Auth(BACKEND_SELECTOR_MOCK_MULTIPLE_CREDS, "email", "secretpass", session)

    client_creds = BACKEND_SELECTOR_MOCK_MULTIPLE_CREDS.client_credentials
    with aioresponses() as m:
        expected = []

        for i in range(len(client_creds)):
            # all but the last one should return 404, as we keep checking until we get a 200 (or run out)
            status = HTTPStatus.NOT_FOUND if i != len(client_creds) else HTTPStatus.OK
            expected.append({"status": status})
            m.post(AUTH_URL, status=status)

        await auth.do_auth(store=False)

        # filter down to just the lines that contain the auth status
        status_logs = [
            line for line in caplog.text.splitlines() if "Auth status" in line
        ]

        # assert we get the expected status codes in the correct order in the logs
        for i, rec in enumerate(expected):
            assert str(rec["status"].value) in status_logs[i]

    await session.close()


async def test_auth_bad_credentials():
    session = aiohttp.ClientSession()
    auth = Auth(BACKEND_SELECTOR_MOCK, "email", "secretpass", session)

    with aioresponses() as m:
        m.post(AUTH_URL, status=HTTPStatus.BAD_REQUEST)

        await auth.do_auth(store=False)

        # with bad request we should not get an access token and not have a SAID list
        assert auth.is_access_token_valid() is False
        assert auth.get_said_list() is None

        # assert that the proper method and url were used
        assert ("POST", URL(AUTH_URL)) in m.requests

        # get the calls for the method/url and assert length
        calls = m.requests[("POST", URL(AUTH_URL))]
        assert len(calls) == 1

        call = calls[0]
        assert call[1]["data"] == AUTH_DATA
        assert call[1]["headers"] == AUTH_HEADERS
        await session.close()
