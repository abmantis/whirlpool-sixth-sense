import json
import logging
from functools import cached_property
from typing import Any

import aiohttp

from whirlpool.eventsocket import EventSocket

from .aircon import Aircon
from .appliance import Appliance
from .auth import Auth
from .backendselector import BackendSelector
from .dryer import Dryer
from .oven import Oven
from .refrigerator import Refrigerator
from .types import ApplianceInfo
from .washer import Washer

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
        self._session: aiohttp.ClientSession = session
        self._event_socket: EventSocket | None = None
        self._aircons: dict[str, Any] = {}
        self._dryers: dict[str, Any] = {}
        self._washers: dict[str, Any] = {}
        self._ovens: dict[str, Any] = {}
        self._refrigerators: dict[str, Any] = {}

    @cached_property
    def all_appliances(self) -> dict[str, Appliance]:
        return {
            **self._aircons,
            **self._dryers,
            **self._washers,
            **self._ovens,
            **self._refrigerators,
        }

    @property
    def aircons(self) -> list[Aircon]:
        return list(self._aircons.values())

    @property
    def dryers(self) -> list[Dryer]:
        return list(self._dryers.values())

    @property
    def washers(self) -> list[Washer]:
        return list(self._washers.values())

    @property
    def ovens(self) -> list[Oven]:
        return list(self._ovens.values())

    @property
    def refrigerators(self) -> list[Refrigerator]:
        return list(self._refrigerators.values())

    def _add_appliance(self, appliance: dict[str, Any]) -> None:
        appliance_data = ApplianceInfo(
            said=appliance["SAID"],
            name=appliance["APPLIANCE_NAME"],
            data_model=appliance["DATA_MODEL_KEY"],
            category=appliance["CATEGORY_NAME"],
            model_number=appliance.get("MODEL_NO", ""),
            serial_number=appliance.get("SERIAL", ""),
        )

        data_model = appliance["DATA_MODEL_KEY"].lower()

        oven_models = [
            "cooking_minerva",
            "cooking_vsi",
            "cooking_u2",
            "ddm_cooking_bio_self_clean_tourmaline_v2",
            "ddm_cooking_bio_g3evo_pyro_bk_v1",
            "ddm_cooking_bio_self_clean_meat_probe_tourmaline_bk_v1",
        ]

        LOGGER.debug("Adding appliance %s", appliance_data)
        if "airconditioner" in data_model:
            self._aircons[appliance_data.said] = Aircon(
                self._backend_selector, self._auth, self._session, appliance_data
            )
        elif "dryer" in data_model:
            self._dryers[appliance_data.said] = Dryer(
                self._backend_selector, self._auth, self._session, appliance_data
            )
        elif "washer" in data_model:
            self._washers[appliance_data.said] = Washer(
                self._backend_selector, self._auth, self._session, appliance_data
            )
        elif any(model in data_model for model in oven_models):
            self._ovens[appliance_data.said] = Oven(
                self._backend_selector, self._auth, self._session, appliance_data
            )
        elif "ddm_ted_refrigerator_v12" in data_model:
            self._refrigerators[appliance_data.said] = Refrigerator(
                self._backend_selector, self._auth, self._session, appliance_data
            )
        else:
            LOGGER.warning("Unsupported appliance data model %s", data_model)
            return

        # Invalidate cached property
        self.__dict__.pop("all_appliances", None)

    async def _get_owned_appliances(self, account_id: str) -> bool:
        async with self._session.get(
            self._backend_selector.get_owned_appliances_url(account_id),
            headers=self._auth.create_headers(),
        ) as r:
            if r.status != 200:
                LOGGER.error("Failed to get appliances: %s", r.status)
                return False

            data = await r.json()
            locations: dict[str, Any] = data[str(account_id)]
            for appliances in locations.values():
                for appliance in appliances:
                    self._add_appliance(appliance)

            return True

    async def _get_shared_appliances(self) -> bool:
        headers = self._auth.create_headers()
        headers["WP-CLIENT-BRAND"] = self._backend_selector.brand.name

        async with self._session.get(
            self._backend_selector.shared_appliances_url, headers=headers
        ) as r:
            if r.status != 200:
                LOGGER.warning(
                    "Failed to get shared appliances: %s. Not all regions/brands"
                    " support sharing, so this can be ignored for those.",
                    r.status,
                )
                return False

            data = await r.json()
            locations: list[dict[str, Any]] = data["sharedAppliances"]
            for appliances in locations:
                for appliance in appliances["appliances"]:
                    self._add_appliance(appliance)

            return True

    async def fetch_appliances(self) -> bool:
        account_id = await self._auth.get_account_id()
        if not account_id:
            return False

        success_owned = await self._get_owned_appliances(account_id)
        success_shared = await self._get_shared_appliances()

        return success_owned or success_shared

    async def fetch_all_data(self):
        for appliance in self.all_appliances.values():
            await appliance.fetch_data()

    async def connect(self):
        """Connect to appliance event listener"""
        await self.start_event_listener()

    async def disconnect(self):
        """Disconnect from appliance event listener"""
        await self.stop_event_listener()

    async def start_event_listener(self):
        """Start the appliance event listener"""
        await self.fetch_all_data()
        if self._event_socket is not None:
            LOGGER.warning("Event socket not None when starting event listener")

        self._event_socket = EventSocket(
            await self._getWebsocketUrl(),
            self._auth,
            list(self.all_appliances.keys()),
            self._event_socket_callback,
            self.fetch_all_data,
            self._session,
        )
        self._event_socket.start()

    async def stop_event_listener(self):
        """Stop the appliance event listener"""
        if self._event_socket is None:
            LOGGER.warning("Event socket is None")
            return
        await self._event_socket.stop()
        self._event_socket = None

    def _event_socket_callback(self, msg: str):
        json_msg = json.loads(msg)
        said = json_msg["said"]
        app = self.all_appliances.get(said)
        if app is None:
            LOGGER.warning("Received message for unknown appliance %s", said)
            return
        app.update_attributes(json_msg["attributeMap"], json_msg["timestamp"])

    async def _getWebsocketUrl(self) -> str:
        DEFAULT_WS_URL = "wss://ws.emeaprod.aws.whrcloud.com/appliance/websocket"
        async with self._session.get(
            self._backend_selector.websocket_url, headers=self._auth.create_headers()
        ) as r:
            if r.status != 200:
                LOGGER.error("Failed to get websocket url: %s", r.status)
                return DEFAULT_WS_URL
            try:
                return json.loads(await r.text())["url"]
            except KeyError:
                LOGGER.exception("Failed to read websocket url")
                return DEFAULT_WS_URL
