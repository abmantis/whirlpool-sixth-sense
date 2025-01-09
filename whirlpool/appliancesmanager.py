import json
import logging
import typing
from typing import Any

import aiohttp
import async_timeout

from whirlpool.eventsocket import EventSocket

from .appliance import Appliance
from .auth import Auth
from .backendselector import BackendSelector
from .types import ApplianceData, ApplianceKind

if typing.TYPE_CHECKING:
    from whirlpool.appliance import Appliance


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
        self._app_dict: dict[str, Any] = {}

    @property
    def all_appliances(self) -> list["Appliance"]:
        return list(self._app_dict.values())

    def _create_headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._auth.get_access_token()}",
            "Content-Type": "application/json",
            "User-Agent": "okhttp/3.12.0",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
        }

        return headers

    def _add_appliance(self, appliance: dict[str, Any]) -> None:
        app_data = ApplianceData(
            said=appliance["SAID"],
            name=appliance["APPLIANCE_NAME"],
            data_model=appliance["DATA_MODEL_KEY"],
            category=appliance["CATEGORY_NAME"],
            model_number=appliance.get("MODEL_NO"),
            serial_number=appliance.get("SERIAL"),
        )

        handler: Appliance = None
        for handler in Appliance.handlers:
            if handler.wants(app_data):
                break
        if not handler:
            LOGGER.warning("Unsupported appliance data model %s", app_data.data_model)
            return

        app = handler(self._backend_selector, self._auth, self._session, app_data)
        self._app_dict[app_data.said] = app

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
        headers = self._create_headers()
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

    def get_appliances(self, kind: ApplianceKind = None) -> list["Appliance"]:
        if not kind:
            return list(self._app_dict.values())
        return [app for app in self._app_dict.values() if app.Kind == kind]

    def get_appliance(self, said: str) -> Appliance:
        return self._app_dict.get(said, None)

    async def fetch_appliances(self):
        account_id = await self._auth.get_account_id()
        if not account_id:
            return False
        success_owned = await self._get_owned_appliances(account_id)
        success_shared = await self._get_shared_appliances()

        return success_owned or success_shared

    async def fetch_all_data(self):
        for appliance in self._app_dict.values():
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
            list(self._app_dict.keys()),
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
        LOGGER.debug(f"Manager event socket message: {msg}")
        json_msg = json.loads(msg)
        said = json_msg["said"]
        app = self._app_dict.get(said)
        if app is None:
            LOGGER.error(f"Received message for unknown appliance {said}")
            return
        app._update_appliance_attributes(json_msg["attributeMap"], json_msg["timestamp"])

    async def _getWebsocketUrl(self) -> str:
        DEFAULT_WS_URL = "wss://ws.emeaprod.aws.whrcloud.com/appliance/websocket"
        async with self._session.get(
            self._backend_selector.ws_url, headers=self._create_headers()
        ) as r:
            if r.status != 200:
                LOGGER.error(f"Failed to get websocket url: {r.status}")
                return DEFAULT_WS_URL
            try:
                return json.loads(await r.text())["url"]
            except KeyError:
                LOGGER.error(f"Failed to get websocket url: {r.status}")
                return DEFAULT_WS_URL

