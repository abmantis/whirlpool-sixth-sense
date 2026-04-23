"""AWS IoT appliances manager: MQTT + capability download + factory."""

from __future__ import annotations

import logging
from collections.abc import Callable
from functools import cached_property
from typing import Any

import aiohttp

from ..aircon import Aircon as AirconABC
from ..auth import Auth as WhirlpoolAuth
from ..dryer import Dryer as DryerABC
from ..microwave import Microwave as MicrowaveABC
from ..oven import Oven as OvenABC
from ..refrigerator import Refrigerator as RefrigeratorABC
from ..types import ApplianceInfo
from ..washer import Washer as WasherABC

# Import subclass modules for side-effect factory registration.
from . import aircon as _aircon  # noqa: F401
from . import dryer as _dryer  # noqa: F401
from . import microwave as _microwave  # noqa: F401
from . import oven as _oven  # noqa: F401
from . import refrigerator as _refrigerator  # noqa: F401
from . import washer as _washer  # noqa: F401
from .appliance import Appliance
from .auth import Auth, AuthException
from .capabilities import (
    CapabilityDownloader,
    CapabilityDownloadError,
)
from .factory import DEFAULT_FACTORY
from .mqttclient import MqttClient
from .things import Things

LOGGER = logging.getLogger(__name__)


class AppliancesManager:
    def __init__(
        self,
        whirlpool_auth: WhirlpoolAuth,
        session: aiohttp.ClientSession,
        appliances_update_callback: Callable[[], None],
    ) -> None:
        self._whirlpool_auth = whirlpool_auth
        self._session = session
        self._update_callback = appliances_update_callback

        self._aws_auth = Auth(self._whirlpool_auth, self._session)
        self._mqtt = MqttClient(self._aws_auth)
        self._capability_downloader = CapabilityDownloader(
            self._mqtt, self._session
        )

        self._aircons: dict[str, Appliance] = {}
        self._dryers: dict[str, Appliance] = {}
        self._washers: dict[str, Appliance] = {}
        self._ovens: dict[str, Appliance] = {}
        self._refrigerators: dict[str, Appliance] = {}
        self._microwaves: dict[str, Appliance] = {}

    # --- category properties --------------------------------------------

    @cached_property
    def all_appliances(self) -> dict[str, Appliance]:
        return {
            **self._aircons,
            **self._dryers,
            **self._washers,
            **self._ovens,
            **self._refrigerators,
            **self._microwaves,
        }

    @property
    def aircons(self) -> list[AirconABC]:
        return list(self._aircons.values())  # type: ignore[return-value]

    @property
    def dryers(self) -> list[DryerABC]:
        return list(self._dryers.values())  # type: ignore[return-value]

    @property
    def washers(self) -> list[WasherABC]:
        return list(self._washers.values())  # type: ignore[return-value]

    @property
    def ovens(self) -> list[OvenABC]:
        return list(self._ovens.values())  # type: ignore[return-value]

    @property
    def refrigerators(self) -> list[RefrigeratorABC]:
        return list(self._refrigerators.values())  # type: ignore[return-value]

    @property
    def microwaves(self) -> list[MicrowaveABC]:
        return list(self._microwaves.values())  # type: ignore[return-value]

    # --- lifecycle -------------------------------------------------------

    async def connect(self) -> bool:
        try:
            if not await self._mqtt.connect():
                LOGGER.error("Failed to connect to MQTT broker")
                return False

            things = await Things(self._aws_auth, self._session).list_things()
        except AuthException as e:
            LOGGER.error("AWS auth failed: %s", e)
            await self._mqtt.disconnect()
            return False
        except Exception:
            LOGGER.exception("Unexpected error during AWS connect")
            await self._mqtt.disconnect()
            return False

        if not things:
            LOGGER.info("No AWS IoT things for this account")
            return True

        for thing in things:
            try:
                await self._add_appliance(thing)
            except Exception:
                LOGGER.exception(
                    "Failed to add AWS appliance %s", thing.get("thingName")
                )
                continue

        return True

    async def disconnect(self) -> None:
        for app in list(self.all_appliances.values()):
            try:
                await app.disconnect()
            except Exception:
                LOGGER.exception("Error disconnecting %s", app.said)
        await self._mqtt.disconnect()

    # --- helpers ---------------------------------------------------------

    async def _add_appliance(self, thing: dict[str, Any]) -> None:
        info = self._build_info(thing)
        attrs = thing.get("attributes") or {}
        cap_part_number = attrs.get("CapabilityPartNumber")
        if not cap_part_number:
            LOGGER.warning(
                "Thing %s has no CapabilityPartNumber; cannot route", info.said
            )
            return

        try:
            profile = await self._capability_downloader.get(
                info.said, info.model_number, cap_part_number
            )
        except CapabilityDownloadError:
            LOGGER.exception(
                "Capability download failed for %s (%s)",
                info.said,
                cap_part_number,
            )
            return

        appliance = DEFAULT_FACTORY.build(self._mqtt, profile, thing, info)
        if appliance is None:
            LOGGER.warning(
                "No AWS appliance class matches %s "
                "(category=%s, addressees=%s, features=%s)",
                info.said,
                info.category,
                sorted(profile.addressees),
                sorted(profile.features),
            )
            return

        await appliance.connect()
        self._register(appliance)

    def _register(self, appliance: Appliance) -> None:
        if isinstance(appliance, MicrowaveABC):
            self._microwaves[appliance.said] = appliance
        elif isinstance(appliance, OvenABC):
            self._ovens[appliance.said] = appliance
        elif isinstance(appliance, AirconABC):
            self._aircons[appliance.said] = appliance
        elif isinstance(appliance, DryerABC):
            self._dryers[appliance.said] = appliance
        elif isinstance(appliance, WasherABC):
            self._washers[appliance.said] = appliance
        elif isinstance(appliance, RefrigeratorABC):
            self._refrigerators[appliance.said] = appliance
        else:
            LOGGER.warning(
                "Built appliance %s does not inherit any known ABC; ignoring",
                appliance.said,
            )
            return

        self.__dict__.pop("all_appliances", None)
        self._update_callback()

    def _build_info(self, thing: dict[str, Any]) -> ApplianceInfo:
        attrs = thing.get("attributes") or {}
        raw_name = attrs.get("Name", "")
        try:
            name = bytes.fromhex(raw_name).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            name = thing.get("thingName", "")
        return ApplianceInfo(
            said=thing.get("thingName", ""),
            name=name,
            category=str(attrs.get("Category", "")).lower(),
            model_number=thing.get("thingTypeName", ""),
            serial_number=attrs.get("Serial", ""),
        )
