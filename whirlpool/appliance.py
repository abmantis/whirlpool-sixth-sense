import json
import logging
from collections.abc import Callable
from typing import Any

import aiohttp
import async_timeout

from .auth import Auth
from .backendselector import BackendSelector
from .types import ApplianceInfo

LOGGER = logging.getLogger(__name__)

REQUEST_RETRY_COUNT = 3

ATTR_ONLINE = "Online"

SETVAL_VALUE_OFF = "0"
SETVAL_VALUE_ON = "1"


class Appliance:
    """Whirlpool appliance class"""

    def __init__(
        self,
        backend_selector: BackendSelector,
        auth: Auth,
        session: aiohttp.ClientSession,
        appliance_info: ApplianceInfo,
    ):
        self._backend_selector = backend_selector
        self._auth = auth
        self._session = session

        self._attr_changed: list[Callable] = []
        self._data_dict: dict = {}
        self.appliance_info = appliance_info

    def __repr__(self):
        return f"<{self.__class__.__name__}> {self.said} | {self.name}"

    @property
    def said(self) -> str:
        """Return Appliance SAID"""
        return self.appliance_info.said

    @property
    def name(self) -> str:
        """Return Appliance name"""
        return self.appliance_info.name

    async def fetch_data(self) -> bool:
        """Fetch appliance data from web api"""
        if not self._session:
            LOGGER.error("Session not started")
            return False
        uri = self._backend_selector.get_appliance_data_url(self.said)
        for _ in range(REQUEST_RETRY_COUNT):
            async with async_timeout.timeout(30):
                async with self._session.get(
                    uri, headers=self._auth.create_headers()
                ) as r:
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

    async def send_attributes(self, attributes: dict[str, str]) -> bool:
        """Send attributes to appliance api"""
        if not self._session:
            LOGGER.error("Session not started")
            return False

        LOGGER.info(f"Sending attributes: {attributes}")

        cmd_data = {
            "body": attributes,
            "header": {"said": self.said, "command": "setAttributes"},
        }
        for _ in range(REQUEST_RETRY_COUNT):
            async with async_timeout.timeout(30):
                async with self._session.post(
                    self._backend_selector.appliance_command_url,
                    json=cmd_data,
                    headers=self._auth.create_headers(),
                ) as r:
                    LOGGER.debug(f"Reply: {await r.text()}")
                    if r.status == 200:
                        return True
                    elif r.status == 401:
                        await self._auth.do_auth()
                        continue
                    LOGGER.error(f"Sending attributes failed ({r.status})")
        return False

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

    def update_attributes(self, attrs: dict[str, Any], timestamp: int):
        for attr, val in attrs.items():
            if self.has_attribute(attr):
                self._set_attribute(attr, str(val), timestamp)

        for callback in self._attr_changed:
            callback()

    def _set_attribute(self, attribute: str, value: str, timestamp: int):
        LOGGER.debug(f"Updating attribute {attribute} with {value} ({timestamp})")
        self._data_dict["attributes"][attribute]["value"] = value
        self._data_dict["attributes"][attribute]["updateTime"] = timestamp

    def _get_attribute(self, attribute: str) -> str | None:
        """Get attribute from local data dictionary"""
        if not self.has_attribute(attribute):
            return None
        return self._data_dict["attributes"][attribute]["value"]

    def _get_int_attribute(self, attribute: str) -> int | None:
        """Get attribute from local data as int"""
        val = self._get_attribute(attribute)
        return None if val is None else int(val)

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
        return self.attr_value_to_bool(self._get_attribute(ATTR_ONLINE))
