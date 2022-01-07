import aiohttp
import asyncio
import async_timeout
import logging
import json
from datetime import datetime, timedelta, timedelta
from typing import Callable

from whirlpool.backendselector import BackendSelector

from .auth import Auth
from .eventsocket import EventSocket

LOGGER = logging.getLogger(__name__)

ATTR_ONLINE = "Online"

SETVAL_VALUE_OFF = "0"
SETVAL_VALUE_ON = "1"


class Appliance:
    def __init__(
        self,
        backend_selector: BackendSelector,
        auth: Auth,
        said: str,
        attr_changed: Callable,
    ):
        self._backend_selector = backend_selector
        self._auth = auth
        self._said = said
        self._attr_changed = attr_changed
        self._data_dict = None

        self._session: aiohttp.ClientSession = None
        self._event_socket = EventSocket(
            auth.get_access_token(), said, self._event_socket_handler
        )

    def _event_socket_handler(self, msg):
        json_msg = json.loads(msg)
        timestamp = json_msg["timestamp"]
        for (attr, val) in json_msg["attributeMap"].items():
            if not self.has_attribute(attr):
                continue
            self._set_attribute(attr, str(val), timestamp)

        if self._attr_changed:
            self._attr_changed()

    def _create_headers(self):
        return {
            "Authorization": "Bearer " + self._auth.get_access_token(),
            "Content-Type": "application/json",
            # "Host": "api.whrcloud.eu",
            "User-Agent": "okhttp/3.12.0",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
        }

    def _set_attribute(self, attribute, value, timestamp):
        LOGGER.debug(f"Updating attribute {attribute} with {value} ({timestamp})")
        self._data_dict["attributes"][attribute]["value"] = value
        self._data_dict["attributes"][attribute]["updateTime"] = timestamp

    @property
    def said(self):
        return self._said

    async def fetch_data(self):
        if not self._session:
            LOGGER.error("Session not started")
            return False

        uri = f"{self._backend_selector.base_url}/api/v1/appliance/{self._said}"
        self._data_dict = None
        async with async_timeout.timeout(30):
            async with self._session.get(uri) as r:
                self._data_dict = json.loads(await r.text())
                if r.status == 200:
                    return True
                LOGGER.error(f"Fetching data failed ({r.status})")
        return False

    async def send_attributes(self, attributes):
        if not self._session:
            LOGGER.error("Session not started")
            return False

        LOGGER.info(f"Sending attributes: {attributes}")

        uri = f"{self._backend_selector.base_url}/api/v1/appliance/command"
        cmd_data = {
            "body": attributes,
            "header": {"said": self._said, "command": "setAttributes"},
        }
        for n in range(3):
            async with async_timeout.timeout(30):
                async with self._session.post(uri, json=cmd_data) as r:
                    LOGGER.debug(f"Reply: {await r.text()}")
                    if r.status == 200:
                        return True
                    elif r.status == 401:
                        await self._auth.do_auth()
                        await self.start_http_session()
                        continue
                    LOGGER.error(f"Sending attributes failed ({r.status})")
        return False

    def get_attribute(self, attribute):
        if not self.has_attribute(attribute):
            return None
        return self._data_dict["attributes"][attribute]["value"]

    def has_attribute(self, attribute):
        return attribute in self._data_dict["attributes"]

    def bool_to_attr_value(self, b: bool):
        return SETVAL_VALUE_ON if b else SETVAL_VALUE_OFF

    def attr_value_to_bool(self, val: str):
        return None if val is None else val == SETVAL_VALUE_ON

    def get_online(self):
        return self.attr_value_to_bool(self.get_attribute(ATTR_ONLINE))

    async def connect(self):
        await self.start_http_session()
        await self.start_event_listener()

    async def disconnect(self):
        await self.stop_http_session()
        await self.stop_event_listener()

    async def start_http_session(self):
        await self.stop_http_session()
        self._session = aiohttp.ClientSession(headers=self._create_headers())

    async def stop_http_session(self):
        if not self._session:
            return
        await self._session.close()
        self._session = None

    async def start_event_listener(self):
        await self.fetch_data()
        self._event_socket.start()

    async def stop_event_listener(self):
        await self._event_socket.stop()
