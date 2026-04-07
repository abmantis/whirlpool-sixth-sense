import logging

import aiohttp

from .aircon import Aircon
from .auth import Auth
from .awsiot.appliancesmanager import AppliancesManager as AwsAppliancesManager
from .backendselector import BackendSelector
from .dryer import Dryer
from .httpapi.appliancesmanager import AppliancesManager as HttpAppliancesManager
from .oven import Oven
from .refrigerator import Refrigerator
from .washer import Washer

LOGGER = logging.getLogger(__name__)


class AppliancesManager:
    def __init__(
        self,
        backend_selector: BackendSelector,
        auth: Auth,
        session: aiohttp.ClientSession,
    ):
        self._http_appliances_manager = HttpAppliancesManager(
            backend_selector, auth, session, self._update_appliances
        )
        self._aws_appliances_manager = AwsAppliancesManager(
            auth, session, self._update_appliances
        )

    # TODO: use cached_property
    @property
    def aircons(self) -> list[Aircon]:
        return (
            self._http_appliances_manager.aircons + self._aws_appliances_manager.aircons
        )

    # TODO: use cached_property
    @property
    def dryers(self) -> list[Dryer]:
        return (
            self._http_appliances_manager.dryers + self._aws_appliances_manager.dryers
        )

    # TODO: use cached_property
    @property
    def washers(self) -> list[Washer]:
        return (
            self._http_appliances_manager.washers + self._aws_appliances_manager.washers
        )

    # TODO: use cached_property
    @property
    def ovens(self) -> list[Oven]:
        return self._http_appliances_manager.ovens + self._aws_appliances_manager.ovens

    # TODO: use cached_property
    @property
    def refrigerators(self) -> list[Refrigerator]:
        return (
            self._http_appliances_manager.refrigerators
            + self._aws_appliances_manager.refrigerators
        )

    def _update_appliances(self) -> None:
        # TODO: invalidate cached properties

        # Invalidate cached properties
        # self.__dict__.pop("aircons", None)
        pass

    async def connect(self):
        """Connect to APIs"""
        if not await self._http_appliances_manager.connect():
            return False
        if not await self._aws_appliances_manager.connect():
            LOGGER.info("No AWS IoT connection. This is expected on some accounts.")
        return True

    async def disconnect(self):
        """Disconnect from APIs"""
        await self._http_appliances_manager.disconnect()
        await self._aws_appliances_manager.disconnect()
