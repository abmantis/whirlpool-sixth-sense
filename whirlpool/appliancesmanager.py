import aiohttp
import asyncio
import async_timeout
import logging
import json
from datetime import datetime, timedelta, timedelta
from typing import Callable

from whirlpool.backendselector import BackendSelector

from .auth import Auth

LOGGER = logging.getLogger(__name__)


class AppliancesManager:
    def __init__(self, backend_selector: BackendSelector, auth: Auth):
        self._backend_selector = backend_selector
        self._auth = auth
        self._aircons = None
        self._washer_dryers = None
        self._ovens = None

    def _create_headers(self):
        return {
            "Authorization": "Bearer " + self._auth.get_access_token(),
            "Content-Type": "application/json",
            # "Host": "api.whrcloud.eu",
            "User-Agent": "okhttp/3.12.0",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
        }

    async def fetch_appliances(self):
        async with aiohttp.ClientSession(headers=self._create_headers()) as session:
            account_id = None
            async with session.get(
                f"{self._backend_selector.base_url}/api/v1/getUserDetails"
            ) as r:
                if r.status != 200:
                    LOGGER.error(f"Failed to get account id: {r.status}")
                    return False
                account_id = json.loads(await r.text())["accountId"]

            async with session.get(
                f"{self._backend_selector.base_url}/api/v1/appliancebyaccount/{account_id}"
            ) as r:
                if r.status != 200:
                    LOGGER.error(f"Failed to get appliances: {r.status}")
                    return False

                self._aircons = []
                self._washer_dryers = []
                self._ovens = []

                locations = json.loads(await r.text())[str(account_id)]
                for appliances in locations.values():
                    for appliance in appliances:
                        appliance_data = {
                            "SAID": appliance["SAID"],
                            "NAME": appliance["APPLIANCE_NAME"],
                            "DATA_MODEL": appliance["DATA_MODEL_KEY"],
                            "CATEGORY": appliance["CATEGORY_NAME"],
                        }
                        data_model = appliance["DATA_MODEL_KEY"].lower()
                        if "airconditioner" in data_model:
                            self._aircons.append(appliance_data)
                        elif "dryer" in data_model or "washer" in data_model:
                            self._washer_dryers.append(appliance_data)
                        elif "cooking_minerva" in data_model or "cooking_vsi" in data_model:
                            self._ovens.append(appliance_data)
                        else:
                            LOGGER.warning(
                                "Unsupported appliance data model %s", data_model
                            )
        return True

    @property
    def aircons(self):
        return self._aircons

    @property
    def washer_dryers(self):
        return self._washer_dryers

    @property
    def ovens(self):
        return self._ovens
