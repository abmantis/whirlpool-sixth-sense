import json
import logging
from datetime import datetime
from typing import Any

import aiohttp
import async_timeout

from .backendselector import BackendSelector, CredentialsDict

LOGGER = logging.getLogger(__name__)

AUTH_JSON_FILE = ".whirlpool_auth.json"


class Auth:
    def __init__(
        self,
        backend_selector: BackendSelector,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
    ):
        self._backend_selector = backend_selector
        self._username = username
        self._password = password
        self._auth_dict: dict[str, Any] = {}
        self._session: aiohttp.ClientSession = session

        self._renew_time: datetime = None

    def _save_auth_data(self):
        with open(AUTH_JSON_FILE, "w") as f:
            json.dump(self._auth_dict, f)

    def _get_auth_body(
        self, refresh_token: str, client_creds: CredentialsDict
    ) -> dict[str, str]:
        if refresh_token:
            LOGGER.info("Using refresh token in auth body")
            auth_data = {"grant_type": "refresh_token", "refresh_token": refresh_token}

        else:
            LOGGER.info("Using user/pass in auth body")
            auth_data = {
                "grant_type": "password",
                "username": self._username,
                "password": self._password,
            }

        auth_data.update(client_creds)  # type: ignore

        return auth_data

    async def _do_auth(self, refresh_token: str) -> dict[str, str | float] | None:
        auth_url = self._backend_selector.auth_url
        auth_header = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "okhttp/3.12.0",
        }

        for client_creds in self._backend_selector.client_credentials:
            auth_data: dict[str, str] = self._get_auth_body(refresh_token, client_creds)
            async with async_timeout.timeout(30):
                async with self._session.post(
                    auth_url, data=auth_data, headers=auth_header
                ) as r:
                    LOGGER.debug("Auth status: " + str(r.status))
                    if r.status == 200:
                        return await r.json()
                    elif refresh_token:
                        return await self._do_auth(refresh_token=None)

        return None

    async def do_auth(self, store: bool = False) -> bool:
        fetched_auth_data = await self._do_auth(
            self._auth_dict.get("refresh_token", None)
        )

        if not fetched_auth_data:
            self._auth_dict = {}
            LOGGER.error("Authentication failed")
            return False

        curr_timestamp = datetime.now().timestamp()
        self._auth_dict = {
            "access_token": fetched_auth_data.get("access_token", ""),
            "refresh_token": fetched_auth_data.get("refresh_token", ""),
            "expire_date": curr_timestamp + fetched_auth_data.get("expires_in", 0),
            "accountId": fetched_auth_data.get("accountId", ""),
            "SAID": fetched_auth_data.get("SAID", []),
        }
        if store:
            self._save_auth_data()
        return True

    async def load_auth_file(self):
        try:
            with open(AUTH_JSON_FILE, "r") as f:
                LOGGER.info("Loading auth from file")
                self._auth_dict = json.load(f)
        except FileNotFoundError:
            pass

        if not self.is_access_token_valid():
            LOGGER.info("Access token expired. Renewing.")
            await self.do_auth()

    def is_access_token_valid(self) -> bool:
        return (
            "access_token" in self._auth_dict
            and self._auth_dict.get("expire_date", 0) > datetime.now().timestamp()
        )

    def get_access_token(self) -> str | None:
        return self._auth_dict.get("access_token", None)

    def get_account_id(self) -> str | None:
        """Returns the accountId value from the `_auth_dict`, or None if not present."""
        return self._auth_dict.get("accountId", None)

    def get_said_list(self) -> list[str]:
        return self._auth_dict.get("SAID", None)
