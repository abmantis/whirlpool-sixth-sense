import sys
from http import HTTPStatus

import pytest
from aioresponses import aioresponses
from yarl import URL

from tests import ACCOUNT_ID
from whirlpool.auth import AccountLockedError, Auth
from whirlpool.backendselector import BackendSelector

AUTH_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "okhttp/3.12.0",
}


def get_auth_url(backend_selector: BackendSelector) -> str:
    return f"{backend_selector.base_url}/oauth/token"


def get_auth_data(backend_selector: BackendSelector) -> dict[str, str]:
    return {
        "client_id": backend_selector.client_credentials[0].client_id,
        "client_secret": backend_selector.client_credentials[0].client_secret,
        "grant_type": "password",
        "username": "email",
        "password": "secretpass",
    }


async def test_auth_success(
    auth: Auth, backend_selector: BackendSelector, aioresponses_mock: aioresponses
):
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

    auth_url = get_auth_url(backend_selector)

    # don't need repeat here because the first one will succeed
    # so we will only call this url once
    aioresponses_mock.post(auth_url, payload=mock_resp_data)

    await auth.do_auth(store=False)
    assert auth.is_access_token_valid()
    assert auth.get_said_list() == ["SAID1", "SAID2"]
    assert str(await auth.get_account_id()) == ACCOUNT_ID

    # assert that the proper method and url were used
    assert ("POST", URL(auth_url)) in aioresponses_mock.requests

    # get the calls for the method/url and assert length
    calls = aioresponses_mock.requests[("POST", URL(auth_url))]
    assert len(calls) == 1

    # actual call, as a tuple
    call = calls[0]
    assert call[1]["data"] == get_auth_data(backend_selector)
    assert call[1]["headers"] == AUTH_HEADERS


async def test_auth_will_check_all_client_creds(
    auth: Auth,
    backend_selector: BackendSelector,
    aioresponses_mock: aioresponses,
    caplog: pytest.LogCaptureFixture,
):
    # need to capture at debug level to get status - we don't return status or have any
    # other good way to check it
    caplog.set_level("DEBUG")

    auth_url = get_auth_url(backend_selector)
    client_creds = backend_selector.client_credentials
    expected = []

    for i in range(len(client_creds)):
        # all but the last one should return 404, as we keep checking until we get a 200
        # (or run out)
        status = HTTPStatus.NOT_FOUND if i != len(client_creds) else HTTPStatus.OK
        expected.append({"status": status})
        aioresponses_mock.post(auth_url, status=status)

    await auth.do_auth(store=False)

    # filter down to just the lines that contain the auth status
    status_logs = [line for line in caplog.text.splitlines() if "Auth status" in line]

    # assert we get the expected status codes in the correct order in the logs
    for i, rec in enumerate(expected):
        status_val = (
            str(rec["status"].value)
            if sys.version_info >= (3, 11)
            else str(rec["status"])
        )
        assert status_val in status_logs[i]


async def test_auth_bad_credentials(
    auth: Auth, backend_selector: BackendSelector, aioresponses_mock: aioresponses
):
    auth_url = get_auth_url(backend_selector)

    # need to repeat for the multiple client credentials mock
    aioresponses_mock.post(auth_url, status=HTTPStatus.BAD_REQUEST, repeat=True)

    await auth.do_auth(store=False)

    # with bad request we should not get an access token and not have a SAID list
    assert auth.is_access_token_valid() is False
    assert auth.get_said_list() is None

    # assert that the proper method and url were used
    assert ("POST", URL(auth_url)) in aioresponses_mock.requests

    # get the calls for the method/url and assert length - should be the same as the
    # number of client credentials
    calls = aioresponses_mock.requests[("POST", URL(auth_url))]
    assert len(calls) == len(backend_selector.client_credentials)

    call = calls[0]
    assert call[1]["data"] == get_auth_data(backend_selector)
    assert call[1]["headers"] == AUTH_HEADERS


async def test_auth_account_locked(
    auth: Auth, backend_selector: BackendSelector, aioresponses_mock: aioresponses
):
    auth_url = get_auth_url(backend_selector)
    aioresponses_mock.post(auth_url, status=HTTPStatus.LOCKED, repeat=True)

    with pytest.raises(AccountLockedError):
        await auth.do_auth(store=False)

    assert auth.is_access_token_valid() is False
    assert auth.get_said_list() is None


async def test_user_details_requested_only_once(
    auth: Auth, backend_selector: BackendSelector, aioresponses_mock: aioresponses
):
    aioresponses_mock.get(
        backend_selector.user_details_url, payload={"accountId": ACCOUNT_ID}
    )

    headers = {
        "Authorization": f"Bearer {auth.get_access_token()}",
        "Content-Type": "application/json",
        "User-Agent": "okhttp/3.12.0",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
    }

    await auth.get_account_id()

    aioresponses_mock.assert_called_with(
        backend_selector.user_details_url, "GET", headers=headers
    )

    assert auth._auth_dict["accountId"] == ACCOUNT_ID

    # aioresponses_mock.clear does not reset the requests list, so I'm
    # just checking that the length doesn't change instead
    curr_request_count = len(aioresponses_mock.requests)

    await auth.get_account_id()

    assert len(aioresponses_mock.requests) == curr_request_count
