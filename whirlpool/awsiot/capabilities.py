"""AWS IoT capability profile — download, parse, and cache.

Whirlpool's cloud exposes per-model "capability files" over MQTT: publish a
request to `api/capability/download/{model}/{said}` with the CapabilityPartNumber,
receive a response carrying an HTTPS URL, fetch the URL for the JSON body.

This module owns that flow and parses the raw files into per-appliance
profiles that callers use to gate setters and route appliances to the
correct subclass.
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
class OptionRange:
    """Inclusive numeric range with a step, as declared under whrOptions."""

    min: int
    max: int
    step: int
    default: int

    def contains(self, value: int) -> bool:
        if not self.min <= value <= self.max:
            return False
        return self.step <= 1 or (value - self.min) % self.step == 0


@dataclass(frozen=True)
class MicrowaveRecipeOptions:
    """Editable options of one cavity recipe (e.g. "microwave", "reheat").

    `power_level` is the editable mwoPowerLevel range, or None when the recipe
    has a fixed power level (listed under nonEditableOptions) that must not be
    sent. `cook_time` is the editable cookTime range in seconds.
    """

    cook_time: OptionRange
    power_level: OptionRange | None = None
    fixed_power_level: int | None = None


@dataclass(frozen=True)
class MicrowaveCapabilityProfile:
    """The capability switches the Microwave class currently uses."""

    part_number: str
    supports_hood_fan: bool
    supports_hood_light_level: bool
    supports_hood_light_color: bool
    supports_quiet_mode: bool
    supports_control_lock: bool
    supports_sabbath_mode: bool
    recipes: dict[str, MicrowaveRecipeOptions] = field(default_factory=dict)


def _read_part_number(raw: dict[str, Any]) -> str:
    part_number = raw.get("partNumber")
    if not isinstance(part_number, str) or not part_number:
        raise CapabilityDownloadError("Capability file missing 'partNumber'")
    return part_number


def _has_section(raw: dict[str, Any], name: str) -> bool:
    section = raw.get(name)
    return isinstance(section, dict) and bool(section)


def _cavity_metas(raw: dict[str, Any]) -> list[dict[str, Any]]:
    cavities = raw.get("cavities")
    if not isinstance(cavities, dict):
        return []
    return [meta for meta in cavities.values() if isinstance(meta, dict)]


def has_microwave_cavity(raw: dict[str, Any]) -> bool:
    """Whether the capability file declares a microwave oven cavity."""
    return any(meta.get("cavityType") == "microwaveOven" for meta in _cavity_metas(raw))


def _option_range(option: Any) -> OptionRange | None:
    if not isinstance(option, dict):
        return None
    rng = option.get("range")
    if not isinstance(rng, dict):
        return None
    try:
        return OptionRange(
            min=int(rng["min"]),
            max=int(rng["max"]),
            step=int(rng.get("step", 1)),
            default=int(rng.get("default", rng["min"])),
        )
    except KeyError, TypeError, ValueError:
        return None


def _parse_recipe_options(recipe: Any) -> MicrowaveRecipeOptions | None:
    if not isinstance(recipe, dict):
        return None
    options = recipe.get("whrOptions")
    if not isinstance(options, dict):
        return None
    required = options.get("requiredOptions")
    required = required if isinstance(required, dict) else {}
    non_editable = options.get("nonEditableOptions")
    non_editable = non_editable if isinstance(non_editable, dict) else {}

    cook_time = _option_range(required.get("cookTime"))
    if cook_time is None:
        # Not a timed recipe (e.g. sensor/auto recipes keyed on amount/weight).
        return None

    fixed_power = non_editable.get("mwoPowerLevel")
    return MicrowaveRecipeOptions(
        cook_time=cook_time,
        power_level=_option_range(required.get("mwoPowerLevel")),
        fixed_power_level=fixed_power if isinstance(fixed_power, int) else None,
    )


def _parse_recipes(raw: dict[str, Any]) -> dict[str, MicrowaveRecipeOptions]:
    """Collect the timed recipes of the microwave cavity, keyed by wire name."""
    recipes: dict[str, MicrowaveRecipeOptions] = {}
    for meta in _cavity_metas(raw):
        if meta.get("cavityType") != "microwaveOven":
            continue
        declared = meta.get("recipes")
        if not isinstance(declared, dict):
            continue
        for name, recipe in declared.items():
            parsed = _parse_recipe_options(recipe)
            if parsed is not None:
                recipes[name] = parsed
    return recipes


def parse_microwave_capability_profile(
    raw: dict[str, Any],
) -> MicrowaveCapabilityProfile:
    """Extract the microwave-relevant switches from a raw capability file."""
    supports_sabbath_mode = any(
        isinstance(meta.get("sabbathRecipes"), dict) and meta["sabbathRecipes"]
        for meta in _cavity_metas(raw)
    )
    return MicrowaveCapabilityProfile(
        part_number=_read_part_number(raw),
        supports_hood_fan=_has_section(raw, "hoodFan"),
        supports_hood_light_level=_has_section(raw, "hoodLight"),
        supports_hood_light_color=_has_section(raw, "hoodLightColor"),
        supports_quiet_mode=raw.get("quietMode") is True,
        supports_control_lock=raw.get("supportsHmiControlLockout") is True,
        supports_sabbath_mode=supports_sabbath_mode,
        recipes=_parse_recipes(raw),
    )


class CapabilityDownloader:
    """Fetches and caches raw capability files per model (part number).

    Issues an MQTT request for a capability file, awaits the response carrying
    a download URL, then fetches the JSON body. Subscribes/unsubscribes
    around each request so subscriptions are not long-term.
    MQTT messages should be delivered to `handle_message()`.
    Raw documents are cached per part number so repeated lookups are served
    without another round-trip; parsing them is the caller's concern.
    """

    def __init__(
        self,
        mqtt_client: Any,
        session: aiohttp.ClientSession,
    ) -> None:
        self._mqtt = mqtt_client
        self._session = session
        self._cache: dict[str, dict[str, Any]] = {}
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
    ) -> dict[str, Any]:
        if capability_part_number in self._cache:
            return self._cache[capability_part_number]

        last_err: Exception | None = None
        for attempt in range(CAPABILITY_DOWNLOAD_RETRIES):
            try:
                raw = await self._download(said, model_number, capability_part_number)
                self._cache[capability_part_number] = raw
                return raw
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
    ) -> dict[str, Any]:
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

            response_code = response.get("responseCode")
            if response_code is not None and response_code != 200:
                raise CapabilityDownloadError(
                    f"Capability request for {said} returned "
                    f"responseCode {response_code}"
                )
            raw = await self._download_file(response)
            _read_part_number(raw)  # sanity-check before caching
            return raw
        finally:
            self._pending.pop(response_topic, None)
            self._mqtt.unsubscribe(response_topic)

    async def _download_file(self, mqtt_response: dict[str, Any]) -> dict[str, Any]:
        # The broker replies with {"responseCode": 200, "downloadUrl": "..."}.
        url = mqtt_response.get("downloadUrl")
        if not isinstance(url, str) or not url.startswith("http"):
            return mqtt_response
        try:
            async with self._session.get(url) as resp:
                if resp.status != 200:
                    raise CapabilityDownloadError(
                        f"Capability URL returned HTTP {resp.status}"
                    )
                text = await resp.text()
        except aiohttp.ClientError as e:
            raise CapabilityDownloadError(
                f"HTTP error downloading capability file: {e}"
            ) from e
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise CapabilityDownloadError(
                f"Capability body is not valid JSON: {e}"
            ) from e
