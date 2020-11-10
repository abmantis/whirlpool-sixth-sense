import aiohttp
import asyncio
import async_timeout
import logging
import json
from datetime import datetime, timedelta, timedelta
from typing import Callable

from .auth import Auth
from .eventsocket import EventSocket

LOGGER = logging.getLogger(__name__)


class Appliance():
    def __init__(self, auth:Auth, said:str, attr_changed: Callable):
        self._auth = auth
        self._said = said
        self._attr_changed = attr_changed
        self._data_dict = None

        self._session: aiohttp.ClientSession = None
        self._event_socked = EventSocket(
            auth.get_access_token(), said, self._event_socket_handler)

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
            'Authorization': 'Bearer ' + self._auth.get_access_token(),
            'Content-Type': 'application/json',
            'Host': 'api.whrcloud.eu',
            'User-Agent': 'okhttp/3.12.0',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
        }

    def _set_attribute(self, attribute, value, timestamp):
        logging.debug(
            f"Updating attribute {attribute} with {value} ({timestamp})")
        self._data_dict["attributes"][attribute]["value"] = value
        self._data_dict["attributes"][attribute]["updateTime"] = timestamp

    @property
    def said(self):
        return self.said

    async def fetch_data(self):
        if not self._session:
            LOGGER.error("Session not started")
            return False

        uri = f'https://api.whrcloud.eu/api/v1/appliance/{self._said}'
        self._data_dict = None
        with async_timeout.timeout(30):
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

        LOGGER.debug(f"Sending attributes: {attributes}")

        uri = 'https://api.whrcloud.eu/api/v1/appliance/command'
        cmd_data = {
            "body": attributes,
            "header": {
                "said": self._said,
                "command": "setAttributes"
            }
        }
        for n in range(3):
            with async_timeout.timeout(30):
                async with self._session.post(uri, json=cmd_data) as r:
                    LOGGER.debug(f"Reply: {await r.text()}")
                    if r.status == 200:
                        return True
                    elif r.status == 401:
                        await self._auth.do_auth()
                        continue
                    LOGGER.error(f"Sending attributes failed ({r.status})")
        return False

    def get_attribute(self, attribute):
        return self._data_dict["attributes"][attribute]["value"]

    def has_attribute(self, attribute):
        return attribute in self._data_dict["attributes"]

    async def connect(self):
        await self.start_http_session()
        await self.start_event_listener()

    async def disconnect(self):
        await self.stop_http_session()
        await self.stop_event_listener()

    async def start_http_session(self):
        self._session = aiohttp.ClientSession(headers=self._create_headers())

    async def stop_http_session(self):
        if not self._session:
            return
        await self._session.close()

    async def start_event_listener(self):
        await self.fetch_data()
        self._event_socked.start()

    async def stop_event_listener(self):
        await self._event_socked.stop()

    #def get_account_id(self, user_details):
        #return user_details["accountId"]

    #def fetch_said(self, account_id):
        #headers = self._create_headers()
        #with requests.session() as s:
        #r = s.get('https://api.whrcloud.eu/api/v1/appliancebyaccount/{0}'.format(accountId), headers=headers)
        #print(r.text)
        #device_said = json.loads(r.text)["accountId"]

    #def fetch_user_details(self):
        #headers = self._create_headers()
        #with requests.session() as s:
        #r = s.get('https://api.whrcloud.eu/api/v1/getUserDetails', headers=headers)
        #return json.loads(r.text)
        #return None
