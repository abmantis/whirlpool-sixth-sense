import asyncio
import logging
from collections.abc import Callable
from functools import cached_property
from typing import Any

import aiohttp

from whirlpool.awsiot.appliance import Appliance
from whirlpool.eventsocket import EventSocket
from whirlpool.types import ApplianceInfo

from ..auth import Auth as WhirlpoolAuth
from .aircon import Aircon
from .auth import Auth, AuthException
from .capabilities import (
    CapabilityDownloader,
    CapabilityDownloadError,
    has_dryer_cavity,
    has_microwave_cavity,
    has_washer_cavity,
    parse_laundry_capability_profile,
    parse_microwave_capability_profile,
)
from .dryer import Dryer
from .microwave import Microwave
from .mqttclient import MqttClient
from .oven import Oven
from .refrigerator import Refrigerator
from .things import Things
from .washer import Washer

LOGGER = logging.getLogger(__name__)


def _is_dryer_model(model_number: str) -> bool:
    """Whether a laundry model number denotes a dryer.

    Whirlpool/Maytag/KitchenAid laundry model numbers encode the product type
    in the third character: "D" for dryers (e.g. MGD/MED/WGD/WED) and "W" for
    washers (e.g. MFW/MHW/WFW/WTW). Used to split the ambiguous "laundry"
    category, since both dryers and washers report category "laundry" on the
    AWS IoT backend (see the Maytag MFW7020RF0 + MGD7020RF0 fixtures).
    """
    return len(model_number) >= 3 and model_number[2:3].upper() == "D"


def _laundry_is_dryer(
    raw_capabilities: dict[str, Any], appliance_data: ApplianceInfo
) -> bool:
    """Whether a laundry appliance is a dryer rather than a washer.

    The capability file declares the cavity it describes ("dryer" or "washer"),
    which is authoritative. Only when neither is declared does this fall back
    to `_is_dryer_model`, whose three-letter assumption silently treats any
    unrecognised model number as a washer.
    """
    if has_dryer_cavity(raw_capabilities):
        return True
    if has_washer_cavity(raw_capabilities):
        return False

    LOGGER.debug(
        "Capability file for %s declares no laundry cavity; "
        "falling back to the model-number heuristic",
        appliance_data.said,
    )
    return _is_dryer_model(appliance_data.model_number)


class AppliancesManager:
    def __init__(
        self,
        whirlpool_auth: WhirlpoolAuth,
        session: aiohttp.ClientSession,
        appliances_update_callback: Callable[[], None],
    ):
        self._whirlpool_auth = whirlpool_auth
        self._session: aiohttp.ClientSession = session
        self._event_socket: EventSocket | None = None
        self._aircons: dict[str, Any] = {}
        self._dryers: dict[str, Any] = {}
        self._washers: dict[str, Any] = {}
        self._ovens: dict[str, Any] = {}
        self._microwaves: dict[str, Any] = {}
        self._refrigerators: dict[str, Any] = {}

        self._aws_auth = Auth(self._whirlpool_auth, self._session)
        self._mqtt = MqttClient(self._aws_auth, self._handle_mqtt_message)
        self._capability_downloader = CapabilityDownloader(self._mqtt, self._session)

    @cached_property
    def all_appliances(self) -> dict[str, Appliance]:
        return {
            **self._aircons,
            **self._dryers,
            **self._washers,
            **self._ovens,
            **self._microwaves,
            **self._refrigerators,
        }

    @property
    def aircons(self) -> list[Aircon]:
        return list(self._aircons.values())

    @property
    def dryers(self) -> list[Dryer]:
        return list(self._dryers.values())

    @property
    def washers(self) -> list[Washer]:
        return list(self._washers.values())

    @property
    def ovens(self) -> list[Oven]:
        return list(self._ovens.values())

    @property
    def microwaves(self) -> list[Microwave]:
        return list(self._microwaves.values())

    @property
    def refrigerators(self) -> list[Refrigerator]:
        return list(self._refrigerators.values())

    async def connect(self) -> bool:
        """Connect to MQTT"""
        try:
            things = Things(self._aws_auth, self._session)
            things_list = await things.list_things()

            if not await self._mqtt.connect():
                LOGGER.error("Failed to connect to MQTT broker")
                return False
        except AuthException as e:
            LOGGER.error("Authentication failed: %s", e)
            return False
        except (TimeoutError, aiohttp.ClientError) as e:
            LOGGER.error("Failed to connect to AWS IoT: %s", e)
            return False

        for thing in things_list:
            await self._add_appliance(thing)

        await asyncio.gather(
            *[appliance.fetch_data() for appliance in self.all_appliances.values()],
        )

        return True

    async def disconnect(self):
        """Disconnect MQTT"""
        await self._mqtt.disconnect()

    async def _add_appliance(self, thing: dict[str, Any]) -> None:
        LOGGER.debug("Adding thing: %s", thing)
        thing_attrs = thing.get("attributes", {})
        try:
            name = bytes.fromhex(thing_attrs.get("Name", "")).decode("utf-8")
        except ValueError, UnicodeDecodeError:
            name = thing["thingName"]

        appliance_data = ApplianceInfo(
            said=thing["thingName"],
            name=name,
            category=thing_attrs.get("Category", "").lower(),
            model_number=thing["thingTypeName"],
            serial_number=thing_attrs.get("Serial", ""),
        )

        cap_part = thing_attrs.get("CapabilityPartNumber")
        if not cap_part:
            LOGGER.error(
                "Thing %s has no CapabilityPartNumber — skipping",
                appliance_data.said,
            )
            return
        try:
            raw_capabilities = await self._capability_downloader.get(
                appliance_data.said, appliance_data.model_number, cap_part
            )
        except CapabilityDownloadError as e:
            LOGGER.error(
                "Capability download failed for %s: %s — skipping",
                appliance_data.said,
                e,
            )
            return

        appliance: Appliance | None = None
        if appliance_data.category == "cooking":
            if has_microwave_cavity(raw_capabilities):
                appliance = Microwave(
                    self._mqtt,
                    appliance_data,
                    parse_microwave_capability_profile(raw_capabilities),
                )
                self._microwaves[appliance_data.said] = appliance
        elif appliance_data.category in ("laundry", "fabriccare"):
            # Both dryers and washers report category "laundry" on the AWS IoT
            # backend. The capability file's cavity says which one it is; the
            # model-number heuristic is only a fallback for capability files
            # that declare neither cavity.
            is_dryer = _laundry_is_dryer(raw_capabilities, appliance_data)
            cavity = "dryer" if is_dryer else "washer"
            try:
                profile = parse_laundry_capability_profile(raw_capabilities, cavity)
            except CapabilityDownloadError:
                # Routed by model number: the cavity the profile needs is absent.
                profile = None

            if is_dryer:
                appliance = Dryer(self._mqtt, appliance_data, profile)
                self._dryers[appliance_data.said] = appliance
            else:
                appliance = Washer(self._mqtt, appliance_data, profile)
                self._washers[appliance_data.said] = appliance
        if appliance is None:
            LOGGER.warning(
                "Unsupported appliance category %s for %s",
                appliance_data.category,
                thing["thingName"],
            )
            return

        await appliance.subscribe_topics()

        # Invalidate cached property
        self.__dict__.pop("all_appliances", None)

    def _handle_mqtt_message(self, topic: str, payload: dict[str, Any]) -> None:
        LOGGER.debug("Received MQTT message on topic %s: %s", topic, payload)

        if self._capability_downloader.handle_message(topic, payload):
            return

        if topic.startswith("$aws/events/presence/"):
            parts = topic.split("/")
            # $aws/events/presence/{connected|disconnected}/{said}
            if len(parts) != 5:
                return
            event, said = parts[3], parts[4]
            appliance = self.all_appliances.get(said)
            if appliance is None:
                return
            appliance.update_online(event == "connected")
            return

        parts = topic.split("/")
        if len(parts) < 3:
            return
        said = parts[2]

        if topic.startswith("cmd/") and "response" in topic:
            # Only a getState response carries the state; plain command acks
            # ({"response": "accepted"}) and rejections ({"errorCode": ...})
            # must not be merged into the appliance state.
            if payload.get("response") != "accepted":
                return
            state = payload.get("payload")
            if not isinstance(state, dict) or not state:
                return
        elif topic.startswith("dt/") and "state/update" in topic:
            state = payload
        else:
            return

        appliance = self.all_appliances.get(said)
        if appliance is None:
            LOGGER.warning("Received message for unknown appliance %s", said)
            return
        appliance.update_state(state)
