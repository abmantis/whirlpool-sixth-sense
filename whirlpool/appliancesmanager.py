import json
import logging
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
from .types import ApplianceData
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
        self._event_socket: EventSocket = None
        self._ac_dict: dict[str, Any] = {}
        self._dr_dict: dict[str, Any] = {}
        self._ov_dict: dict[str, Any] = {}
        self._rf_dict: dict[str, Any] = {}
        self._wr_dict: dict[str, Any] = {}

    @property
    def all_appliances(self) -> list[Appliance]:
        return {
            **self._ac_dict,
            **self._dr_dict,
            **self._ov_dict,
            **self._rf_dict,
            **self._wr_dict,
        }.values()

    @property
    def aircons(self) -> list[Aircon]:
        return self._ac_dict.values()

    @property
    def dryers(self) -> list[Dryer]:
        return self._dr_dict.values()

    @property
    def ovens(self) -> list[Oven]:
        return self._ov_dict.values()

    @property
    def refrigerators(self) -> list[Refrigerator]:
        return self._rf_dict.values()

    @property
    def washers(self) -> list[Washer]:
        return self._wr_dict.values()

    def _add_appliance(self, appliance: dict[str, Any]) -> None:
        app_data = ApplianceData(
            said=appliance["SAID"],
            name=appliance["APPLIANCE_NAME"],
            data_model=appliance["DATA_MODEL_KEY"],
            category=appliance["CATEGORY_NAME"],
            model_number=appliance.get("MODEL_NO"),
            serial_number=appliance.get("SERIAL"),
        )

        data_model = appliance["DATA_MODEL_KEY"].lower()

        oven_models = [
            "cooking_minerva",
            "cooking_vsi",
            "cooking_u2",
            "ddm_cooking_bio_self_clean_tourmaline_v2",
        ]

        if "airconditioner" in data_model:
            self._ac_dict[app_data.said] = Aircon(
                self._backend_selector, self._auth, self._session, app_data
            )
        elif "dryer" in data_model:
            self._dr_dict[app_data.said] = Dryer(
                self._backend_selector, self._auth, self._session, app_data
            )
        elif any(model in data_model for model in oven_models):
            self._ov_dict[app_data.said] = Oven(
                self._backend_selector, self._auth, self._session, app_data
            )
        elif "ddm_ted_refrigerator_v12" in data_model:
            self.rf_dict[app_data.said] = Refrigerator(
                self._backend_selector, self._auth, self._session, app_data
            )
        elif "washer" in data_model:
            self._wr_dict[app_data.said] = Washer(
                self._backend_selector, self._auth, self._session, app_data
            )
        else:
            LOGGER.warning("Unsupported appliance data model %s", data_model)
            return

    async def _get_owned_appliances(self, account_id: str) -> bool:
        async with self._session.get(
            self._backend_selector.get_owned_appliances_url(account_id),
            headers=self._auth._create_headers(),
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
        headers = self._auth._create_headers()
        headers["WP-CLIENT-BRAND"] = self._backend_selector.brand.name

        async with self._session.get(
            self._backend_selector.get_shared_appliances_url, headers=headers
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

    async def fetch_all_data(self):
        for appliance in self.all_appliances:
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
            list({
                **self._ac_dict,
                **self._dr_dict,
                **self._ov_dict,
                **self._rf_dict,
                **self._wr_dict,
            }.keys()),
            self._event_socket_callback,
            self.fetch_all_data,
            self._session,
        )
        self._event_socket.start()

    async def stop_event_listener(self):
        """Stop the appliance event listener"""
        await self._event_socket.stop()
        self._event_socket = None

    def _event_socket_callback(self, msg: str):
        json_msg = json.loads(msg)
        said = json_msg["said"]
        app = {
            **self._ac_dict,
            **self._dr_dict,
            **self._ov_dict,
            **self._rf_dict
            **self._wr_dict,
        }.get(said)
        if app is None:
            LOGGER.error(f"Received message for unknown appliance {said}")
            return
        app._update_appliance_attributes(
            json_msg["attributeMap"],
            json_msg["timestamp"]
        )

    async def _getWebsocketUrl(self) -> str:
        DEFAULT_WS_URL = "wss://ws.emeaprod.aws.whrcloud.com/appliance/websocket"
        async with self._session.get(
            self._backend_selector.ws_url, headers=self._auth._create_headers()
        ) as r:
            if r.status != 200:
                LOGGER.error(f"Failed to get websocket url: {r.status}")
                return DEFAULT_WS_URL
            try:
                return json.loads(await r.text())["url"]
            except KeyError:
                LOGGER.error(f"Failed to get websocket url: {r.status}")
                return DEFAULT_WS_URL

