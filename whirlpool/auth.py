import aiohttp
import asyncio
import async_timeout
import logging
import json
from datetime import datetime, timedelta, timedelta

from whirlpool.backendselector import BackendSelector

LOGGER = logging.getLogger(__name__)

AUTH_JSON_FILE = ".whirlpool_auth.json"
AUTO_REFRESH_DELTA = timedelta(minutes=15)


class Auth:
    def __init__(self, backend_selector: BackendSelector, username, password):
        self._backend_selector = backend_selector
        self._username = username
        self._password = password
        self._auth_dict = {}

        self._renew_time: datetime = None
        self._auto_renewal_task: asyncio.Task = None

    async def _do_auto_renewal(self):
        if self._renew_time > datetime.now():
            time_to = (self._renew_time - datetime.now()).seconds
            LOGGER.info("Renewing in %ds", time_to)
            await asyncio.sleep(time_to)
        await self.do_auth()

    def _schedule_auto_renewal(self):
        return  # disable for now and rely on on-demand renewal

        if not self.is_access_token_valid():
            LOGGER.warn("Access token is not valid, renewing now")
            self._renew_time = datetime.now()
        else:
            expire_date = datetime.fromtimestamp(self._auth_dict.get("expire_date", 0))
            self._renew_time = expire_date - AUTO_REFRESH_DELTA
            LOGGER.info(
                "Expire date is %s, renewing at %s", expire_date, self._renew_time
            )

        self.cancel_auto_renewal()
        self._auto_renewal_task = asyncio.create_task(self._do_auto_renewal())

    def _save_auth_data(self):
        with open(AUTH_JSON_FILE, "w") as f:
            json.dump(self._auth_dict, f)

    async def _do_auth(self, refresh_token):
        auth_url = f"{self._backend_selector.base_url}/oauth/token"
        auth_header = {
            "Content-Type": "application/x-www-form-urlencoded",
            # "Brand": "Whirlpool",
            # "WP-CLIENT-REGION": "EMEA",
            # "WP-CLIENT-BRAND": "WHIRLPOOL",
            # "WP-CLIENT-COUNTRY": "EN",
        }

        auth_data = {
            "client_id": self._backend_selector.client_id,
            "client_secret": self._backend_selector.client_secret,
        }

        if refresh_token:
            LOGGER.info("Fetching auth with refresh token")
            auth_data.update(
                {
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                }
            )
        else:
            LOGGER.info("Fetching auth with user/pass")
            auth_data.update(
                {
                    "grant_type": "password",
                    "username": self._username,
                    "password": self._password,
                }
            )

        session = aiohttp.ClientSession()

        try:
            async with async_timeout.timeout(30):
                async with session.post(
                    auth_url, data=auth_data, headers=auth_header
                ) as r:
                    LOGGER.debug("Auth status: " + str(r.status))
                    if r.status == 200:
                        return json.loads(await r.text())
                    elif refresh_token:
                        return await self._do_auth(refresh_token=None)
                    return None

        finally:
            await session.close()

    async def do_auth(self, store=True):
        fetched_auth_data = await self._do_auth(
            self._auth_dict.get("refresh_token", None)
        )

        if not fetched_auth_data:
            self._auth_dict = {}
            LOGGER.error("Authentication failed")
            return

        curr_timestamp = datetime.now().timestamp()
        self._auth_dict = {
            "access_token": fetched_auth_data.get("access_token", ""),
            "refresh_token": fetched_auth_data.get("refresh_token", ""),
            "expire_date": curr_timestamp + fetched_auth_data.get("expires_in", ""),
            "accountId": fetched_auth_data.get("accountId", ""),
            "SAID": fetched_auth_data.get("SAID", ""),
        }
        if store:
            self._save_auth_data()
        self._schedule_auto_renewal()

    async def load_auth_file(self):
        try:
            with open(AUTH_JSON_FILE, "r") as f:
                LOGGER.info("Loading auth from file")
                self._auth_dict = json.load(f)
        except FileNotFoundError:
            pass

        if self.is_access_token_valid():
            self._schedule_auto_renewal()
        else:
            LOGGER.info("Access token expired. Renewing.")
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

    def cancel_auto_renewal(self):
        if self._auto_renewal_task:
            self._auto_renewal_task.cancel()
