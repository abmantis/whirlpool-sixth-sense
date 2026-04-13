import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from whirlpool_aws.types import ApplianceInfo

LOGGER = logging.getLogger(__name__)


class Appliance(ABC):
    """Whirlpool appliance class"""

    def __init__(
        self,
        appliance_info: ApplianceInfo,
    ):
        self.appliance_info = appliance_info
        self._attr_changed: list[Callable] = []

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

    @abstractmethod
    async def fetch_data(self) -> bool:
        """Fetch appliance data from web api"""
        pass

    @abstractmethod
    def get_online(self) -> bool | None:
        """Get the online state of the appliance"""
        pass

    @abstractmethod
    def get_raw_data(self) -> dict[str, Any] | None:
        """Return the raw data dict for the appliance."""
        pass

    def register_attr_callback(self, update_callback: Callable):
        """Register state update callback."""
        self._attr_changed.append(update_callback)
        LOGGER.debug("Registered attr callback")

    def unregister_attr_callback(self, update_callback: Callable):
        """Unregister state update callback."""
        try:
            self._attr_changed.remove(update_callback)
            LOGGER.debug("Unregistered attr callback")
        except ValueError:
            LOGGER.error("Attr callback not found")
