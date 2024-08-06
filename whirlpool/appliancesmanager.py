import logging
from typing import Any

import aiohttp

from .auth import Auth
from .backendselector import BackendSelector

LOGGER = logging.getLogger(__name__)


class AppliancesManager:
    def __init__(
        self,
        backend_selector: BackendSelector,
        auth: Auth,
        session: aiohttp.ClientSession,
    ):
        self._backend_selector = backend_selector
        self._auth = auth
        self._aircons: list[dict[str, Any]] = []
        self._washer_dryers: list[dict[str, Any]] = []
        self._ovens: list[dict[str, Any]] = []
        self._session: aiohttp.ClientSession = session

    def _create_headers(self, include_wp_brand_name: bool = False):
        headers = {
            "Authorization": f"Bearer {self._auth.get_access_token()}",
            "Content-Type": "application/json",
            "User-Agent": "okhttp/3.12.0",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
        }

        if include_wp_brand_name:
            headers["WP-CLIENT-BRAND"] = self._backend_selector.brand.name

        return headers

    def _add_appliance(self, appliance: dict[str, Any]) -> None:
        appliance_data = {
            "SAID": appliance["SAID"],
            "NAME": appliance["APPLIANCE_NAME"],
            "DATA_MODEL": appliance["DATA_MODEL_KEY"],
            "CATEGORY": appliance["CATEGORY_NAME"],
            "MODEL_NUMBER": appliance.get("MODEL_NO"),
            "SERIAL_NUMBER": appliance.get("SERIAL"),
        }
        data_model = appliance["DATA_MODEL_KEY"].lower()

        if "airconditioner" in data_model:
            self._aircons.append(appliance_data)
            return

        if "dryer" in data_model or "washer" in data_model:
            self._washer_dryers.append(appliance_data)
            return
        oven_models = [
            "cooking_minerva",
            "cooking_vsi",
            "cooking_u2",
            "ddm_cooking_bio_self_clean_tourmaline_v2",
        ]
        if any(model in data_model for model in oven_models):
            self._ovens.append(appliance_data)
            return

        LOGGER.warning("Unsupported appliance data model %s", data_model)

    async def _get_owned_appliances(self, account_id: str) -> bool:
        async with self._session.get(
            self._backend_selector.get_owned_appliances_url(account_id),
            headers=self._create_headers(),
        ) as r:
            if r.status != 200:
                LOGGER.error(f"Failed to get appliances: {r.status}")
                return False

            data = await r.json()
            locations: dict[str, Any] = data[str(account_id)]
            for appliances in locations.values():
                for appliance in appliances:
                    self._add_appliance(appliance)

            return True

    async def _get_shared_appliances(self) -> bool:
        headers = self._create_headers(include_wp_brand_name=True)

        async with self._session.get(
            self._backend_selector.shared_appliances_url, headers=headers
        ) as r:
            if r.status != 200:
                LOGGER.error(f"Failed to get shared appliances: {r.status}")
                return False

            data = await r.json()
            locations: list[dict[str, Any]] = data["sharedAppliances"]
            for appliances in locations:
                for appliance in appliances["appliances"]:
                    self._add_appliance(appliance)

            return True

    async def fetch_appliances(self):
        account_id = await self._auth.get_account_id()
        if not account_id:
            return False
        success_owned = await self._get_owned_appliances(account_id)
        success_shared = await self._get_shared_appliances()

        return success_owned or success_shared

    @property
    def aircons(self):
        return self._aircons

    @property
    def washer_dryers(self):
        return self._washer_dryers

    @property
    def ovens(self):
        return self._ovens
