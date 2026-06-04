"""AWS IoT capability profile — download, parse, and cache.

Whirlpool's cloud exposes per-model "capability files" over MQTT: publish a
request to `api/capability/download/{model}/{said}` with the CapabilityPartNumber,
receive a response carrying an HTTPS URL, fetch the URL for the JSON body.

This module owns that flow and produces a normalized CapabilityProfile that
callers use to gate setters and route appliances to the correct subclass.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

import aiohttp

LOGGER = logging.getLogger(__name__)

CAPABILITY_DOWNLOAD_TIMEOUT = 10.0
CAPABILITY_DOWNLOAD_RETRIES = 3


class CapabilityDownloadError(Exception):
    """Raised when a capability file cannot be retrieved or parsed."""


@dataclass(frozen=True)
class CapabilityProfile:
    """Normalized capability metadata for a single appliance model."""

    part_number: str
    features: frozenset[str]
    addressees: frozenset[str]
    commands: dict[str, frozenset[str]] = field(default_factory=dict)

    def has_feature(self, feature: str) -> bool:
        return feature in self.features

    def has_addressee(self, addressee: str) -> bool:
        return addressee in self.addressees

    def supports_command(self, addressee: str, command: str) -> bool:
        return command in self.commands.get(addressee, frozenset())


def parse_capability_profile(raw: dict[str, Any]) -> CapabilityProfile:
    """Normalize a raw capability JSON dict into a CapabilityProfile.

    Supports two schemas:
      1. Real-device files: top-level `partNumber`, `appliance.features` dict,
         `cavities` dict for cavity addressees, top-level `hoodFan`/`hoodLight`
         /`hoodLightColor` dicts.
      2. Test fixtures: `capabilityPartNumber` string, `features` list,
         optional `addressees` dict mapping addressee → command list.
    """
    part_number = raw.get("partNumber") or raw.get("capabilityPartNumber")
    if not isinstance(part_number, str) or not part_number:
        raise CapabilityDownloadError(
            "Capability file missing 'partNumber' / 'capabilityPartNumber'"
        )

    features: set[str] = set()
    addressees: set[str] = set()
    commands: dict[str, frozenset[str]] = {}

    # Real-device schema
    if "cavities" in raw or "appliance" in raw:
        app = raw.get("appliance", {})
        if isinstance(app, dict):
            feat_dict = app.get("features")
            if isinstance(feat_dict, dict):
                features.update(feat_dict.keys())
        cavities = raw.get("cavities")
        if isinstance(cavities, dict):
            for addr, meta in cavities.items():
                addressees.add(addr)
                if isinstance(meta, dict):
                    cmds = meta.get("commands")
                    if isinstance(cmds, list):
                        commands[addr] = frozenset(cmds)
        for addr in ("hoodFan", "hoodLight", "hoodLightColor"):
            section = raw.get(addr)
            if isinstance(section, dict):
                addressees.add(addr)
                cmds = section.get("commands")
                if isinstance(cmds, list):
                    commands[addr] = frozenset(cmds)

    # Test-fixture schema (also merges with real schema if both keys present)
    feat_list = raw.get("features")
    if isinstance(feat_list, list):
        features.update(str(f) for f in feat_list)
    fixture_addr = raw.get("addressees")
    if isinstance(fixture_addr, dict):
        for addr, cmds in fixture_addr.items():
            addressees.add(addr)
            if isinstance(cmds, list):
                commands[addr] = frozenset(cmds)

    return CapabilityProfile(
        part_number=part_number,
        features=frozenset(features),
        addressees=frozenset(addressees),
        commands=commands,
    )


class CapabilityDownloader:
    """Fetches and caches capability profiles per model (part number).

    Issues an MQTT request for a capability file, awaits the response carrying
    a download URL, then fetches and parses the JSON body. Subscribes/unsubscribes
    around each request so subscriptions are not long-term.
    MQTT messages should be delivered to `handle_message()`.
    Results are cached per part number so repeated lookups are served without another
    round-trip.
    """

    def __init__(
        self,
        mqtt_client: Any,
        session: aiohttp.ClientSession,
        *,
        timeout: float | None = None,
        retries: int | None = None,
    ) -> None:
        self._mqtt = mqtt_client
        self._session = session
        self._timeout = (
            timeout if timeout is not None else CAPABILITY_DOWNLOAD_TIMEOUT
        )
        self._retries = (
            retries if retries is not None else CAPABILITY_DOWNLOAD_RETRIES
        )
        self._cache: dict[str, CapabilityProfile] = {}
        self._pending: dict[str, asyncio.Future[dict[str, Any]]] = {}

    def handle_message(self, topic: str, payload: dict[str, Any]) -> bool:
        """Deliver an incoming MQTT message to a pending download, if any.

        Returns True when the message was consumed (caller should stop routing).
        """
        future = self._pending.get(topic)
        if future is None or future.done():
            return False
        future.set_result(payload)
        return True

    async def get(
        self, said: str, model_number: str, capability_part_number: str
    ) -> CapabilityProfile:
        if capability_part_number in self._cache:
            return self._cache[capability_part_number]

        last_err: Exception | None = None
        for attempt in range(self._retries):
            try:
                profile = await self._download(
                    said, model_number, capability_part_number
                )
                self._cache[capability_part_number] = profile
                return profile
            except (TimeoutError, CapabilityDownloadError) as e:
                last_err = e
                LOGGER.debug(
                    "Capability download attempt %d/%d for %s failed: %s",
                    attempt + 1,
                    self._retries,
                    said,
                    e,
                )
                if attempt < self._retries - 1:
                    await asyncio.sleep(2**attempt)

        raise CapabilityDownloadError(
            f"Capability download for {said} failed after {self._retries} "
            f"attempts: {last_err}"
        )

    async def _download(
        self, said: str, model_number: str, capability_part_number: str
    ) -> CapabilityProfile:
        request_topic = f"api/capability/download/{model_number}/{said}"
        response_topic = f"{request_topic}/response"

        future: asyncio.Future[dict[str, Any]] = (
            asyncio.get_running_loop().create_future()
        )
        self._pending[response_topic] = future
        self._mqtt.subscribe(response_topic)
        try:
            self._mqtt.publish(
                request_topic,
                {
                    "requestId": str(uuid.uuid4()),
                    "capabilityPartNumber": capability_part_number,
                },
            )
            try:
                response = await asyncio.wait_for(future, timeout=self._timeout)
            except TimeoutError as e:
                raise CapabilityDownloadError(
                    f"Timed out waiting for capability response for {said}"
                ) from e

            raw = await self._download_file(response)
            return parse_capability_profile(raw)
        finally:
            self._pending.pop(response_topic, None)
            self._mqtt.unsubscribe(response_topic)

    async def _download_file(self, mqtt_response: dict[str, Any]) -> dict[str, Any]:
        url = mqtt_response.get("url")
        if not isinstance(url, str) or not url.startswith("http"):
            return mqtt_response
        async with self._session.get(url) as resp:
            if resp.status != 200:
                raise CapabilityDownloadError(
                    f"Capability URL returned HTTP {resp.status}"
                )
            text = await resp.text()
            try:
                return json.loads(text)
            except json.JSONDecodeError as e:
                raise CapabilityDownloadError(
                    f"Capability body is not valid JSON: {e}"
                ) from e
