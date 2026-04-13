"""Capability file download, parsing, and caching.

Issue #122: the Whirlpool cloud exposes capability files via an MQTT
request/response topic pair, not via HTTPS. This module owns that flow
and produces a normalized CapabilityProfile that the factory consumes
to route appliances to the right subclass.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import aiohttp

from .mqttclient import MqttClient

LOGGER = logging.getLogger(__name__)

CAPABILITY_DOWNLOAD_TIMEOUT = 10.0


class CapabilityDownloadError(Exception):
    """Raised when a capability file cannot be retrieved or parsed."""


@dataclass(frozen=True)
class CapabilityProfile:
    """Parsed capability file for a single appliance model."""

    part_number: str
    raw: dict[str, Any]
    features: frozenset[str]
    addressees: frozenset[str]
    commands: dict[str, frozenset[str]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def has_feature(self, feature: str) -> bool:
        return feature in self.features

    def has_addressee(self, addressee: str) -> bool:
        return addressee in self.addressees

    def supports_command(self, addressee: str, command: str) -> bool:
        return command in self.commands.get(addressee, frozenset())


def parse_capability_profile(raw: dict[str, Any]) -> CapabilityProfile:
    """Normalize a raw capability file dict into a CapabilityProfile.

    Supports two schemas:
      1. Real device files: top-level `partNumber`, `cavities` dict for cavity
         addressees, top-level `hoodFan`/`hoodLight`/`hoodLightColor` dicts,
         `appliance.features` dict.
      2. Test fixtures: `capabilityPartNumber`, `features` list, `addressees` dict.
    """
    # --- Part number ---
    part_number = raw.get("partNumber") or raw.get("capabilityPartNumber")
    if not isinstance(part_number, str) or not part_number:
        raise CapabilityDownloadError(
            "Capability file is missing 'partNumber' or 'capabilityPartNumber'"
        )

    features: set[str] = set()
    addressee_names: set[str] = set()
    commands: dict[str, frozenset[str]] = {}

    # --- Real schema: top-level cavities / hoodFan / appliance.features ---
    if "cavities" in raw or "appliance" in raw:
        # Features from appliance.features (keys are feature names)
        app_features = raw.get("appliance", {})
        if isinstance(app_features, dict):
            feat_dict = app_features.get("features") or {}
            if isinstance(feat_dict, dict):
                features.update(feat_dict.keys())

        # Cavities → addressees
        cavities = raw.get("cavities") or {}
        if isinstance(cavities, dict):
            for cav_name, cav_spec in cavities.items():
                addressee_names.add(cav_name)
                if isinstance(cav_spec, dict):
                    # Derive microwaveOven feature if mwoConfig present
                    if "mwoConfig" in cav_spec:
                        features.add("microwaveOven")
                    # Recipes → commands for this cavity
                    recipes = cav_spec.get("recipes") or {}
                    if isinstance(recipes, dict):
                        commands[cav_name] = frozenset(recipes.keys())

        # Top-level addressees: hoodFan, hoodLight, hoodLightColor, etc.
        _KNOWN_ADDRESSEES = ("hoodFan", "hoodLight", "hoodLightColor")
        for addr in _KNOWN_ADDRESSEES:
            if addr in raw and isinstance(raw[addr], dict):
                addressee_names.add(addr)

        # Metadata from misc top-level keys
        metadata: dict[str, Any] = {}
        for key in ("generatorInfo", "productVariant", "autoShutOffTime",
                     "supportsTemperatureUnitChange", "supportsHmiControlLockout",
                     "quietMode", "sabbathMode", "contentManagementProject"):
            if key in raw:
                metadata[key] = raw[key]

    # --- Test fixture schema: flat features list + addressees dict ---
    else:
        features_list = raw.get("features") or []
        if isinstance(features_list, list):
            features.update(str(f) for f in features_list)

        addressees_obj = raw.get("addressees") or {}
        if isinstance(addressees_obj, dict):
            for name, spec in addressees_obj.items():
                addressee_names.add(str(name))
                cmds: list[str] = []
                if isinstance(spec, dict):
                    cmd_list = spec.get("commands") or []
                    if isinstance(cmd_list, list):
                        cmds = [str(c) for c in cmd_list]
                commands[str(name)] = frozenset(cmds)

        metadata = raw.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}

    return CapabilityProfile(
        part_number=part_number,
        raw=raw,
        features=frozenset(features),
        addressees=frozenset(addressee_names),
        commands=commands,
        metadata=metadata,
    )


class CapabilityDownloader:
    """Downloads capability files over MQTT, parses them, caches the result."""

    def __init__(
        self,
        mqtt: MqttClient,
        session: aiohttp.ClientSession,
        cache_dir: Path | None = None,
        timeout: float = CAPABILITY_DOWNLOAD_TIMEOUT,
    ) -> None:
        self._mqtt = mqtt
        self._session = session
        self._cache_dir = cache_dir
        self._timeout = timeout
        self._memory_cache: dict[str, CapabilityProfile] = {}

    async def get(
        self,
        said: str,
        model_number: str,
        capability_part_number: str,
    ) -> CapabilityProfile:
        cached = self._memory_cache.get(capability_part_number)
        if cached is not None:
            LOGGER.debug("Capability cache hit (memory) for %s", capability_part_number)
            return cached

        disk_hit = self._load_from_disk(capability_part_number)
        if disk_hit is not None:
            LOGGER.debug("Capability cache hit (disk) for %s", capability_part_number)
            profile = parse_capability_profile(disk_hit)
            self._memory_cache[capability_part_number] = profile
            return profile

        LOGGER.debug(
            "Downloading capability file %s for said=%s", capability_part_number, said
        )
        raw = await self._download(said, model_number, capability_part_number)
        profile = parse_capability_profile(raw)
        self._memory_cache[capability_part_number] = profile
        self._save_to_disk(capability_part_number, raw)
        return profile

    async def _download(
        self, said: str, model_number: str, capability_part_number: str
    ) -> dict[str, Any]:
        response_topic = f"api/capability/download/{model_number}/{said}/response"
        request_topic = f"api/capability/download/{model_number}/{said}"

        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()

        async def handler(topic: str, payload: dict[str, Any]) -> None:
            if topic != response_topic:
                return
            if not future.done():
                future.set_result(payload)

        self._mqtt.add_message_handler(handler)
        try:
            await self._mqtt.subscribe(response_topic)
            await self._mqtt.publish(
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
                    f"Timed out waiting for capability file for {said}"
                ) from e

            download_url = response.get("url") or response.get("downloadUrl")
            if isinstance(download_url, str) and download_url.startswith("http"):
                return await self._fetch_capability_url(download_url)
            # Fall-through: the response itself may BE the capability.
            return response
        finally:
            self._mqtt.remove_message_handler(handler)
            await self._mqtt.unsubscribe(response_topic)

    async def _fetch_capability_url(self, url: str) -> dict[str, Any]:
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

    def _load_from_disk(self, part_number: str) -> dict[str, Any] | None:
        if self._cache_dir is None:
            return None
        path = self._cache_dir / f"{part_number}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as e:
            LOGGER.warning("Ignoring unreadable capability cache %s: %s", path, e)
            return None

    def _save_to_disk(self, part_number: str, raw: dict[str, Any]) -> None:
        if self._cache_dir is None:
            return
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            (self._cache_dir / f"{part_number}.json").write_text(json.dumps(raw))
        except OSError as e:
            LOGGER.warning(
                "Failed to write capability cache for %s: %s", part_number, e
            )
