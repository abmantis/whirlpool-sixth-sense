import aiohttp
import async_timeout
import logging
import json
from typing import Callable

from .backendselector import BackendSelector

from .auth import Auth
from .eventsocket import EventSocket

LOGGER = logging.getLogger(__name__)

ATTR_ONLINE = "Online"

SETVAL_VALUE_OFF = "0"
SETVAL_VALUE_ON = "1"


class Appliance:
    """Whirlpool appliance class."""

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
        self._attr_changed: list(Callable) = []
        self._event_socket = None
        self._data_dict = None

        self._session: aiohttp.ClientSession = session

    def register_attr_callback(self, update_callback: Callable):
        """Register Callback function."""
        self._attr_changed.append(update_callback)
        LOGGER.debug("Registered attr callback")

    def unregister_attr_callback(self, update_callback: Callable):
        """Unregister callback function."""
        if self._attr_changed:
            try:
                self._attr_changed.remove(update_callback)
                LOGGER.debug("Unregistered attr callback")
            except ValueError:
                LOGGER.error("Attr callback not found")
        LOGGER.error("_attr_changed is None when unregistering callback")

    def _event_socket_handler(self, msg):
        json_msg = json.loads(msg)
        timestamp = json_msg["timestamp"]
        for attr, val in json_msg["attributeMap"].items():
            if not self.has_attribute(attr):
                continue
            self._set_attribute(attr, str(val), timestamp)

        for callback in self._attr_changed:
            callback()

    def _create_headers(self):
        return {
            "Authorization": "Bearer " + self._auth.get_access_token(),
            "Content-Type": "application/json",
            "User-Agent": "okhttp/3.12.0",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
        }

    def _set_attribute(self, attribute, value, timestamp):
        LOGGER.debug("Updating attribute %s with %s (%s)", attribute, value, timestamp)
        self._data_dict["attributes"][attribute]["value"] = value
        self._data_dict["attributes"][attribute]["updateTime"] = timestamp

    async def _getWebsocketUrl(self):
        DEFAULT_WS_URL = "wss://ws.emeaprod.aws.whrcloud.com/appliance/websocket"
        async with self._session.get(
            f"{self._backend_selector.base_url}/api/v1/client_auth/webSocketUrl",
            headers=self._create_headers(),
        ) as r:
            if r.status != 200:
                LOGGER.error("Failed to get websocket url: %s", r.status)
                return DEFAULT_WS_URL
            try:
                return json.loads(await r.text())["url"]
            except KeyError:
                LOGGER.error("Failed to get websocket url: %s", r.status)
                return DEFAULT_WS_URL

    @property
    def said(self):
        """SAID for appliance."""
        return self._said

    async def fetch_data(self):
        """Fetch and update internal data structures."""
        if not self._session:
            LOGGER.error("Session not started")
            return False

        uri = f"{self._backend_selector.base_url}/api/v1/appliance/{self._said}"
        async with async_timeout.timeout(30):
            async with self._session.get(uri, headers=self._create_headers()) as r:
                self._data_dict = json.loads(await r.text())
                if r.status == 200:
                    return True
                elif r.status == 401:
                    await self._auth.do_auth()

                LOGGER.error("Fetching data failed (%s)", r.status)
        return False

    async def send_attributes(self, attributes):
        """Send attributes to API."""
        if not self._session:
            LOGGER.error("Session not started")
            return False

        LOGGER.info("Sending attributes: %s", attributes)

        uri = f"{self._backend_selector.base_url}/api/v1/appliance/command"
        cmd_data = {
            "body": attributes,
            "header": {"said": self._said, "command": "setAttributes"},
        }
        for n in range(3):
            async with async_timeout.timeout(30):
                async with self._session.post(
                    uri, json=cmd_data, headers=self._create_headers()
                ) as r:
                    LOGGER.debug("Reply: %s", await r.text())
                    if r.status == 200:
                        return True
                    elif r.status == 401:
                        await self._auth.do_auth()
                        continue
                    LOGGER.error("Sending attributes failed (%s)", r.status)
        return False

    def get_attribute(self, attribute):
        """Get attribute from internal data."""
        if not self.has_attribute(attribute):
            return None
        return self._data_dict["attributes"][attribute]["value"]

    def has_attribute(self, attribute):
        """Is attribute in dictionary."""
        if self._data_dict:
            return attribute in self._data_dict.get("attributes")
        return None

    def bool_to_attr_value(self, b: bool):
        """Convert bool to attribute value."""
        return SETVAL_VALUE_ON if b else SETVAL_VALUE_OFF

    def attr_value_to_bool(self, val: str):
        """Convert attribute value to a bool value."""
        return None if val is None else val == SETVAL_VALUE_ON

    def get_online(self):
        """Get appliance online value."""
        return self.attr_value_to_bool(self.get_attribute(ATTR_ONLINE))

    async def connect(self):
        """Connect to API and start event listener."""
        await self.start_event_listener()

    async def disconnect(self):
        """Disconnect event listener."""
        await self.stop_event_listener()

    async def start_event_listener(self):
        """Fetch first pass of data and start the event listener."""
        await self.fetch_data()
        if self._event_socket is not None:
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
        """Stop the event listener."""
        await self._event_socket.stop()
        self._event_socket = None
