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

                locations = json.loads(await r.text())[str(account_id)]
                for appliances in locations.values():
                    for appliance in appliances:
                        appliance_data = {
                            "SAID": appliance["SAID"],
                            "NAME": appliance["APPLIANCE_NAME"],
                        }
                        category_name = appliance["CATEGORY_NAME"]
                        if "AirConditioner" in category_name:
                            self._aircons.append(appliance_data)
                        elif "FabricCare" in category_name:
                            self._washer_dryers.append(appliance_data)
                        else:
                            LOGGER.warning(
                                "Unsupported appliance category %s", category_name
                            )
        return True

    @property
    def aircons(self):
        return self._aircons

    @property
    def washer_dryers(self):
        return self._washer_dryers
