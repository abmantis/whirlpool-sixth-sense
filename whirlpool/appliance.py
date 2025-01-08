import logging
import typing
from collections.abc import Callable

from .types import ApplianceData

if typing.TYPE_CHECKING:
    from .appliancesmanager import AppliancesManager

LOGGER = logging.getLogger(__name__)

ATTR_ONLINE = "Online"

SETVAL_VALUE_OFF = "0"
SETVAL_VALUE_ON = "1"


class Appliance:
    """Whirlpool appliance class"""

    def __init__(
        self,
        app_manager: "AppliancesManager",
        appliance_data: ApplianceData,
    ):
        self._app_manager = app_manager
        self._attr_changed: list[Callable] = []
        self._data_dict: dict = {}
        self._appliance_data = appliance_data

    @property
    def said(self) -> str:
        """Return Appliance SAID"""
        return self._appliance_data.said

    @property
    def name(self) -> str:
        """Return Appliance name"""
        return self._appliance_data.name

    async def fetch_data(self):
        await self._app_manager.fetch_appliance_data(self)

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

