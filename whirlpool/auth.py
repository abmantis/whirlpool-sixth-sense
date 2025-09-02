import json
import logging
from datetime import datetime
from typing import Any

import aiohttp
import async_timeout

from .backendselector import BackendConfig, BackendSelector

LOGGER = logging.getLogger(__name__)

AUTH_JSON_FILE = ".whirlpool_auth.json"


class AccountLockedError(Exception):
    """Exception for authentication failure due to account being locked."""


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

        self._renew_time: datetime | None = None

    def _save_auth_data(self):
        with open(AUTH_JSON_FILE, "w") as f:
            json.dump(self._auth_dict, f)

    def _get_auth_body(
        self, refresh_token: str | None, client_creds: BackendConfig
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

        auth_data.update(
            {
                "client_id": client_creds.client_id,
                "client_secret": client_creds.client_secret,
            }
        )

        return auth_data

    async def _do_auth(self, refresh_token: str | None) -> dict[str, str] | None:
        auth_url = self._backend_selector.oauth_token_url
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
                    if r.status == 423:
                        raise AccountLockedError()
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
            "expire_date": curr_timestamp + int(fetched_auth_data.get("expires_in", 0)),
            "accountId": fetched_auth_data.get("accountId", ""),
            "SAID": fetched_auth_data.get("SAID", ""),
        }
        if store:
            self._save_auth_data()
        return True

    async def load_auth_file(self):
        try:
            with open(AUTH_JSON_FILE) as f:
                LOGGER.info("Loading auth from file")
                self._auth_dict = json.load(f)
        except FileNotFoundError:
            pass

        if not self.is_access_token_valid():
            LOGGER.info("Access token expired. Renewing.")
            await self.do_auth()

    def is_access_token_valid(self):
        return (
            "access_token" in self._auth_dict
            and self._auth_dict.get("expire_date", 0) > datetime.now().timestamp()
        )

    def get_access_token(self):
        return self._auth_dict.get("access_token", None)

    async def get_account_id(self) -> str | None:
        """Returns the accountId value from the `_auth_dict` if it exists,
        otherwise fetches it from the backend and returns it.
        """
        if self._auth_dict.get("accountId"):
            return self._auth_dict.get("accountId")

        headers = {
            "Authorization": f"Bearer {self.get_access_token()}",
            "Content-Type": "application/json",
            "User-Agent": "okhttp/3.12.0",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
        }

        async with self._session.get(
            self._backend_selector.user_details_url, headers=headers
        ) as r:
            if r.status != 200:
                LOGGER.error(f"Failed to get account id: {r.status}")
                return None
            data = await r.json()
            self._auth_dict["accountId"] = data["accountId"]
            return self._auth_dict["accountId"]

    def get_said_list(self):
        return self._auth_dict.get("SAID", None)

    def create_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.get_access_token()}",
            "Content-Type": "application/json",
            "User-Agent": "okhttp/3.12.0",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
        }
