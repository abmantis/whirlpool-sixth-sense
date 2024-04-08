import json
import logging
from typing import Callable

import aiohttp
import async_timeout

from .auth import Auth
from .backendselector import BackendSelector
from .eventsocket import EventSocket

LOGGER = logging.getLogger(__name__)

ATTR_ONLINE = "Online"

SETVAL_VALUE_OFF = "0"
SETVAL_VALUE_ON = "1"
REQUEST_RETRY_COUNT = 3


class Appliance:
    """Whirlpool appliance class"""

    def __init__(
        self,
        backend_selector: BackendSelector,
        auth: Auth,
        said: str,
        session: aiohttp.ClientSession,
    ):
        self._backend_selector = backend_selector
        self._auth = auth
        self._said = said
        self._attr_changed: list[Callable] = []
        self._event_socket: EventSocket = None
        self._data_dict: dict = {}

        self._session: aiohttp.ClientSession = session

    @property
    def said(self) -> str:
        """Return Appliance SAID"""
        return self._said

    def register_attr_callback(self, update_callback: Callable):
        """Register Callback function."""
        self._attr_changed.append(update_callback)
        LOGGER.debug("Registered attr callback")

    def unregister_attr_callback(self, update_callback: Callable):
        """Unregister callback function."""
        try:
            self._attr_changed.remove(update_callback)
            LOGGER.debug("Unregistered attr callback")
        except ValueError:
            LOGGER.error("Attr callback not found")

    def _set_attribute(self, attribute: str, value: str, timestamp: int):
        LOGGER.debug(f"Updating attribute {attribute} with {value} ({timestamp})")
        self._data_dict["attributes"][attribute]["value"] = value
        self._data_dict["attributes"][attribute]["updateTime"] = timestamp

    def get_attribute(self, attribute: str) -> str | None:
        """Get attribute from local data dictionary"""
        if not self.has_attribute(attribute):
            return None
        return self._data_dict["attributes"][attribute]["value"]

    def has_attribute(self, attribute: str) -> bool:
        """Check for attribute in local data dictionary"""
        if not self._data_dict:
            LOGGER.error("No data available")
            return False
        return attribute in self._data_dict.get("attributes", {})

    def bool_to_attr_value(self, b: bool) -> str:
        """Convert bool to attribute value"""
        return SETVAL_VALUE_ON if b else SETVAL_VALUE_OFF

    def attr_value_to_bool(self, val: str | None) -> bool | None:
        """Convert attribute value to bool"""
        return None if val is None else val == SETVAL_VALUE_ON

    def get_online(self) -> bool | None:
        """Get online state for appliance"""
        return self.attr_value_to_bool(self.get_attribute(ATTR_ONLINE))

    async def fetch_data(self) -> bool:
        """Fetch appliance data from web api"""
        if not self._session:
            LOGGER.error("Session not started")
            return False

        uri = f"{self._backend_selector.base_url}/api/v1/appliance/{self._said}"
        for _ in range(REQUEST_RETRY_COUNT):
            async with async_timeout.timeout(30):
                async with self._session.get(uri, headers=self._create_headers()) as r:
                    if r.status == 200:
                        self._data_dict = json.loads(await r.text())
                        for callback in self._attr_changed:
                            callback()
                        return True
                    elif r.status == 401:
                        LOGGER.error(
                            "Fetching data failed (%s). Doing reauth", r.status
                        )
                        await self._auth.do_auth()
                    else:
                        LOGGER.error("Fetching data failed (%s)", r.status)
        return False

    async def send_attributes(self, attributes: str) -> bool:
        """Send attributes to appliance api"""
        if not self._session:
            LOGGER.error("Session not started")
            return False

        LOGGER.info(f"Sending attributes: {attributes}")

        uri = f"{self._backend_selector.base_url}/api/v1/appliance/command"
        cmd_data = {
            "body": attributes,
            "header": {"said": self._said, "command": "setAttributes"},
        }
        for _ in range(REQUEST_RETRY_COUNT):
            async with async_timeout.timeout(30):
                async with self._session.post(
                    uri, json=cmd_data, headers=self._create_headers()
                ) as r:
                    LOGGER.debug(f"Reply: {await r.text()}")
                    if r.status == 200:
                        return True
                    elif r.status == 401:
                        await self._auth.do_auth()
                        continue
                    LOGGER.error(f"Sending attributes failed ({r.status})")
        return False

    async def connect(self):
        """Connect to appliance event listener"""
        await self.start_event_listener()

    async def disconnect(self):
        """Disconnect from appliance event listener"""
        await self.stop_event_listener()

    async def start_event_listener(self):
        """Start the appliance event listener"""
        await self.fetch_data()
        if self._event_socket != None:
            LOGGER.warning("Event socket not None when starting event listener")

        self._event_socket = EventSocket(
            await self._getWebsocketUrl(),
            self._auth,
            self._said,
            self._event_socket_handler,
            self.fetch_data,
            self._session,
        )
        self._event_socket.start()

    async def stop_event_listener(self):
        """Stop the appliance event listener"""
        await self._event_socket.stop()
        self._event_socket = None

    def _event_socket_handler(self, msg: str):
        json_msg = json.loads(msg)
        timestamp = json_msg["timestamp"]
        for attr, val in json_msg["attributeMap"].items():
            if not self.has_attribute(attr):
                continue
            self._set_attribute(attr, str(val), timestamp)

        for callback in self._attr_changed:
            callback()

    def _create_headers(self) -> dict[str, str]:
        return {
            "Authorization": "Bearer {0}".format(self._auth.get_access_token()),
            "Content-Type": "application/json",
            "User-Agent": "okhttp/3.12.0",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
        }

    async def _getWebsocketUrl(self) -> str:
        DEFAULT_WS_URL = "wss://ws.emeaprod.aws.whrcloud.com/appliance/websocket"
        async with self._session.get(
            f"{self._backend_selector.base_url}/api/v1/client_auth/webSocketUrl",
            headers=self._create_headers(),
        ) as r:
            if r.status != 200:
                LOGGER.error(f"Failed to get websocket url: {r.status}")
                return DEFAULT_WS_URL
            try:
                return json.loads(await r.text())["url"]
            except KeyError:
                LOGGER.error(f"Failed to get websocket url: {r.status}")
                return DEFAULT_WS_URL
