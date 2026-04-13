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
from .dryer import Dryer
from .mqttclient import MqttClient
from .oven import Oven
from .refrigerator import Refrigerator
from .things import Things
from .washer import Washer

LOGGER = logging.getLogger(__name__)


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
        self._refrigerators: dict[str, Any] = {}

        self._aws_auth = Auth(self._whirlpool_auth, self._session)
        self._mqtt = MqttClient(self._aws_auth, self._handle_mqtt_message)

    @cached_property
    def all_appliances(self) -> dict[str, Appliance]:
        return {
            **self._aircons,
            **self._dryers,
            **self._washers,
            **self._ovens,
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

        for thing in things_list:
            await self._add_appliance(thing)

        # TODO: remove this after appliances are implemented (so CLI can be used)
        await asyncio.sleep(5)
        return True

    async def disconnect(self):
        """Disconnect MQTT"""
        if not self._mqtt.is_connected:
            LOGGER.debug("MQTT client not connected")
            return False

        await self._mqtt.disconnect()

    async def _add_appliance(self, thing: dict[str, Any]) -> None:
        LOGGER.debug("Adding thing: %s", thing)
        thing_attrs = thing.get("attributes", {})
        try:
            name = bytes.fromhex(thing_attrs.get("Name", "")).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            name = thing["thingName"]

        appliance_data = ApplianceInfo(
            said=thing["thingName"],
            name=name,
            category=thing_attrs.get("Category", "").lower(),
            model_number=thing["thingTypeName"],
            serial_number=thing_attrs.get("Serial", ""),
        )

        if appliance_data.category == "airconditioner":
            appliance = Aircon(self._mqtt, appliance_data)
            self._aircons[appliance_data.said] = appliance
        elif appliance_data.category == "cooking":
            appliance = Oven(self._mqtt, appliance_data)
            self._ovens[appliance_data.said] = appliance
        # elif appliance_data.category == "dishwasher":
        elif appliance_data.category == "fabriccare":
            appliance = Dryer(self._mqtt, appliance_data)
            self._dryers[appliance_data.said] = appliance
        elif appliance_data.category == "laundry":
            appliance = Washer(self._mqtt, appliance_data)
            self._washers[appliance_data.said] = appliance
        elif appliance_data.category == "refrigerator":
            appliance = Refrigerator(self._mqtt, appliance_data)
            self._refrigerators[appliance_data.said] = appliance
        else:
            LOGGER.warning(
                "Unsupported appliance category %s for %s",
                appliance_data.category,
                thing["thingName"],
            )
            return

        await appliance.subscribe_topics()
        await appliance.fetch_data()

        # Invalidate cached property
        self.__dict__.pop("all_appliances", None)

    def _handle_mqtt_message(self, topic: str, payload: dict[str, Any]) -> None:
        LOGGER.debug("Received MQTT message on topic %s: %s", topic, payload)
        parts = topic.split("/")
        if len(parts) < 3:
            return
        said = parts[2]

        if topic.startswith("cmd/") and "response" in topic:
            state = payload.get("payload", {})
        elif topic.startswith("dt/") and "state/update" in topic:
            state = payload
        else:
            return

        appliance = self.all_appliances.get(said)
        if appliance is None:
            LOGGER.warning("Received message for unknown appliance %s", said)
            return
        appliance.update_state(state)
