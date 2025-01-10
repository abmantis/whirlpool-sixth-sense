import json
import logging
from collections.abc import Callable
from typing import Any, ClassVar

import aiohttp
import async_timeout

from .auth import Auth
from .backendselector import BackendSelector
from .types import ApplianceData

LOGGER = logging.getLogger(__name__)

REQUEST_RETRY_COUNT = 3

ATTR_ONLINE = "Online"

SETVAL_VALUE_OFF = "0"
SETVAL_VALUE_ON = "1"


class Appliance:
    """Whirlpool appliance class"""

    handlers: ClassVar[list[type["Appliance"]]] = list()

    def __init_subclass__(cls: type["Appliance"], **kwargs):
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "Kind"):
            LOGGER.error("appliance class missing Kind attribute")
            return

        if hasattr(cls, "Model"):
            cls.handlers.insert(0, cls)
        else:
            cls.handlers.append(cls)

    @staticmethod
    def wants(appliance_data: ApplianceData) -> bool:
        return False

    def __init__(
        self,
        backend_selector: BackendSelector,
        auth: Auth,
        session: aiohttp.ClientSession,
        appliance_data: ApplianceData,
    ) -> None:
        self._backend_selector: BackendSelector = backend_selector
        self._auth: Auth = auth
        self._session: aiohttp.ClientSession = session

        self._attr_changed: list[Callable] = []
        self._data_dict: dict = {}
        self._data_model: dict | None = None
        self._data_attrs: dict = None
        self._appliance_data = appliance_data

    @property
    def said(self) -> str:
        """Return Appliance SAID"""
        return self._appliance_data.said

    @property
    def name(self) -> str:
        """Return Appliance name"""
        return self._appliance_data.name

    @property
    def data_model(self) -> dict[str, Any] | None:
        """Return this appliances data model"""
        return self._data_model

    @property
    def data_attrs(self) -> dict[str, str] | None:
        """Return this appliances data model"""
        return self._data_attrs

    async def fetch_data(self) -> bool:
        """Fetch appliance data from web api"""
        if not self._session:
            LOGGER.error("Session not started")
            return False

        uri = self._backend_selector.get_appliance_data_url(self.said)
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

    async def fetch_data_model(self) -> bool:
        """Fetch appliance data model from web api"""
        if not self._session:
            LOGGER.error("Session not started")
            return False

        headers = self._create_headers()
        headers["WP-CLIENT-COUNTRY"] = self._backend_selector.region.name
        headers["WP-CLIENT-BRAND"] = self._backend_selector.brand.name
        data={"saIdList": [self.said]}

        model = None
        url=self._backend_selector.get_data_model_url
        for _ in range(REQUEST_RETRY_COUNT):
            async with async_timeout.timeout(30):
                async with self._session.post(url, json=data, headers=headers) as r:
                    if r.status == 200:
                        model = json.loads(await r.text())
                        break
                    elif r.status == 403:
                        LOGGER.error(
                            "Fetching data failed (%s).", r.status
                        )
                        return False
                    elif r.status == 401:
                        LOGGER.error(
                            "Fetching data failed (%s). Doing reauth", r.status
                        )
                        await self._auth.do_auth()
                    else:
                        LOGGER.error("Fetching data failed (%s)", r.status)
                        return False

        if self.said not in model:
            LOGGER.warning("SAID not found in data model...ignoring device")
            return False

        model = model[self.said]
        if "dataModel" not in model or "attributes" not in model["dataModel"]:
            LOGGER.warning("Missing dataModel -> attributes...ignoring device")
            return False

        attrs = {}
        for attr in model["dataModel"]["attributes"]:
            if "Instance" in attr and attr["Instance"]:
                if "M2MAttributeName" in attr:
                    attrs[attr["M2MAttributeName"]] = attr

        self._data_model = model
        self._data_attrs = attrs
        return True

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
                    self._backend_selector.post_appliance_command_url,
                    json=cmd_data,
                    headers=self._create_headers(),
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

    def _create_headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._auth.get_access_token()}",
            "Content-Type": "application/json",
            "User-Agent": "okhttp/3.12.0",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
        }
        return headers

    def _update_appliance_attributes(self, attrs: dict[str, str], timestamp: str):
        for attr, val in attrs.items():
            if self.has_attribute(attr):
                self._set_attribute(attr, str(val), timestamp)

        for callback in self._attr_changed:
            callback()

    def _set_attribute(self, attribute: str, value: str, timestamp: str):
        LOGGER.debug(f"Updating attribute {attribute} with {value} ({timestamp})")
        self._data_dict["attributes"][attribute]["value"] = value
        self._data_dict["attributes"][attribute]["updateTime"] = timestamp

    def get_attribute(self, attribute: str) -> str | None:
        """Get attribute from local data dictionary"""
        if not self.has_attribute(attribute):
            return None
        return self._data_dict["attributes"][attribute]["value"]

    async def set_attribute(self, attr: str, val: str) -> None:
        await self.send_attributes(self, {attr: val})

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

    def get_boolean(self, attr: str) -> bool:
        return self.get_attribute(attr) == "1"

    async def set_boolean(self, attr: str, val: bool) -> None:
        await self.send_attributes(
            self, {attr: self.bool_to_attr_value(val)}
        )

    def get_enum(self, attr: str) -> str | None:
        val = self.get_attribute(attr)
        if not val or attr not in self.data_attrs:
            return None
        if "EnumValues" not in self.data_attrs[attr]:
            return None
        return self.data_attrs[attr]["EnumValues"].get(val, None)

    def get_enum_values(self, attr: str) -> list[str] | None:
        if attr not in self.data_attrs:
            return None
        if "EnumValues" not in self.data_attrs[attr]:
            return None
        return list(self.data_attrs[attr]["EnumValues"].values())

    async def set_enum(self, attr: str, val: str) -> None:
        if attr not in self.data_attrs:
            return None
        if "EnumValues" not in self.data_attrs[attr]:
            return None
        for k, v in self.data_attrs[attr]["EnumValues"]:
            if v == val:
                await self.send_attributes(self, {attr: k})

    def get_int(self, attr: str) -> int | None:
        val = self.get_attribute(attr)
        if not val:
            return None
        try:
            return int(val)
        except Exception:
            return None

    async def set_int(self, attr: str, val: int) -> None:
        await self.send_attributes(self, {attr: str(val)})

