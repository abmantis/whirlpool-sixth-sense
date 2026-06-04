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
    """Normalized capability metadata for a single appliance model.

    Holds only generic primitives read directly from the real capability
    file. Appliance classes layer their own semantic ``supports_*`` helpers
    on top of these queries.
    """

    part_number: str
    features: frozenset[str]
    cavity_types: frozenset[str]
    sections: frozenset[str]
    flags: dict[str, bool] = field(default_factory=dict)
    sabbath_recipes_present: bool = False

    def has_feature(self, feature: str) -> bool:
        return feature in self.features

    def has_cavity_type(self, cavity_type: str) -> bool:
        return cavity_type in self.cavity_types

    def has_section(self, name: str) -> bool:
        return name in self.sections

    def flag(self, name: str, default: bool = False) -> bool:
        return self.flags.get(name, default)


def parse_capability_profile(raw: dict[str, Any]) -> CapabilityProfile:
    """Normalize a raw Whirlpool capability JSON dict into a CapabilityProfile.

    The real schema is: top-level ``partNumber``; ``appliance.features`` dict;
    ``cavities`` dict whose members may carry a ``cavityType`` and a
    ``sabbathRecipes`` dict; top-level control sections such as ``hoodFan`` /
    ``hoodLight`` / ``hoodLightColor``; and top-level boolean capability flags
    such as ``quietMode`` and ``supportsHmiControlLockout``.
    """
    part_number = raw.get("partNumber")
    if not isinstance(part_number, str) or not part_number:
        raise CapabilityDownloadError("Capability file missing 'partNumber'")

    features: set[str] = set()
    app = raw.get("appliance")
    if isinstance(app, dict):
        feat_dict = app.get("features")
        if isinstance(feat_dict, dict):
            features.update(feat_dict.keys())

    cavity_types: set[str] = set()
    sabbath_recipes_present = False
    cavities = raw.get("cavities")
    if isinstance(cavities, dict):
        for meta in cavities.values():
            if not isinstance(meta, dict):
                continue
            cavity_type = meta.get("cavityType")
            if isinstance(cavity_type, str) and cavity_type:
                cavity_types.add(cavity_type)
            sabbath = meta.get("sabbathRecipes")
            if isinstance(sabbath, dict) and sabbath:
                sabbath_recipes_present = True

    sections = {k for k, v in raw.items() if isinstance(v, dict) and v}
    flags = {k: v for k, v in raw.items() if isinstance(v, bool)}

    return CapabilityProfile(
        part_number=part_number,
        features=frozenset(features),
        cavity_types=frozenset(cavity_types),
        sections=frozenset(sections),
        flags=flags,
        sabbath_recipes_present=sabbath_recipes_present,
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
    ) -> None:
        self._mqtt = mqtt_client
        self._session = session
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
        for attempt in range(CAPABILITY_DOWNLOAD_RETRIES):
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
                    CAPABILITY_DOWNLOAD_RETRIES,
                    said,
                    e,
                )
                if attempt < CAPABILITY_DOWNLOAD_RETRIES - 1:
                    await asyncio.sleep(2**attempt)

        raise CapabilityDownloadError(
            f"Capability download for {said} failed after "
            f"{CAPABILITY_DOWNLOAD_RETRIES} attempts: {last_err}"
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
                response = await asyncio.wait_for(
                    future, timeout=CAPABILITY_DOWNLOAD_TIMEOUT
                )
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
