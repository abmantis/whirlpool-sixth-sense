import aiohttp
import asyncio
import async_timeout
import logging
import json
from datetime import datetime, timedelta, timedelta

LOGGER = logging.getLogger(__name__)

AUTH_JSON_FILE = "auth.json"


class Auth:
    def __init__(self, username, password):
        self._username = username
        self._password = password
        self._auth_dict = {}
        self._session: aiohttp.ClientSession = None

    def _save_auth_data(self):
        with open(AUTH_JSON_FILE, "w") as f:
            json.dump(self._auth_dict, f)

    async def _do_auth(self, refresh_token):
        if not self._session:
            self._session = aiohttp.ClientSession()

        auth_url = "https://api.whrcloud.eu/oauth/token"
        auth_header = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Brand": "Whirlpool",
            "WP-CLIENT-REGION": "EMEA",
            "WP-CLIENT-BRAND": "WHIRLPOOL",
            "WP-CLIENT-COUNTRY": "EN",
        }

        auth_data = {
            "client_id": "whirlpool_android",
            "client_secret": "i-eQ8MD4jK4-9DUCbktfg-t_7gvU-SrRstPRGAYnfBPSrHHt5Mc0MFmYymU2E2qzif5cMaBYwFyFgSU6NTWjZg",
        }

        if refresh_token:
            LOGGER.debug("Fetching auth with refresh token")
            auth_data.update(
                {
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                }
            )
        else:
            LOGGER.debug("Fetching auth with user/pass")
            auth_data.update(
                {
                    "grant_type": "password",
                    "username": self._username,
                    "password": self._password,
                }
            )

        with async_timeout.timeout(30):
            async with self._session.post(auth_url, data=auth_data, headers=auth_header) as r:
                LOGGER.debug("Auth status: " + str(r.status))
                if r.status == 200:
                    return json.loads(await r.text())
                elif refresh_token:
                    return await self._do_auth(refresh_token=None)

    async def do_auth(self):
        fetched_auth_data = await self._do_auth(self._auth_dict.get("refresh_token", None))
        curr_timestamp = datetime.now().timestamp()
        self._auth_dict = {
            "access_token": fetched_auth_data.get("access_token", ""),
            "refresh_token": fetched_auth_data.get("refresh_token", ""),
            "expire_date": curr_timestamp + fetched_auth_data.get("expires_in", ""),
            "accountId": fetched_auth_data.get("accountId", ""),
            "SAID": fetched_auth_data.get("SAID", ""),
        }
        self._save_auth_data()

    async def load_auth_file(self):
        try:
            with open(AUTH_JSON_FILE, "r") as f:
                LOGGER.debug("Loading auth from file")
                self._auth_dict = json.load(f)
        except FileNotFoundError:
            pass

        if not self.is_access_token_valid():
            LOGGER.debug("Access token expired. Renewing.")
            await self.do_auth()

    def is_access_token_valid(self):
        return (
            "access_token" in self._auth_dict
            and self._auth_dict.get("expire_date", 0) > datetime.now().timestamp()
        )

    def get_access_token(self):
        return self._auth_dict.get("access_token", None)

    def get_said_list(self):
        return self._auth_dict.get("SAID", None)
