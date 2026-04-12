"""Capability file download, parsing, and caching.

Issue #122: the Whirlpool cloud exposes capability files via an MQTT
request/response topic pair, not via HTTPS. This module owns that flow
and produces a normalized CapabilityProfile that the factory consumes
to route appliances to the right subclass.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

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

    Shape assumptions (provisional until real files are captured):
      - `capabilityPartNumber`: str (required)
      - `features`: list[str]
      - `addressees`: dict[name -> {"commands": list[str]}]
      - `metadata`: optional dict
    """
    part_number = raw.get("capabilityPartNumber")
    if not isinstance(part_number, str) or not part_number:
        raise CapabilityDownloadError(
            "Capability file is missing 'capabilityPartNumber'"
        )

    features_list = raw.get("features") or []
    if not isinstance(features_list, list):
        raise CapabilityDownloadError("Capability 'features' is not a list")
    features = frozenset(str(f) for f in features_list)

    addressees_obj = raw.get("addressees") or {}
    if not isinstance(addressees_obj, dict):
        raise CapabilityDownloadError("Capability 'addressees' is not a dict")

    commands: dict[str, frozenset[str]] = {}
    for name, spec in addressees_obj.items():
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
        features=features,
        addressees=frozenset(commands.keys()),
        commands=commands,
        metadata=metadata,
    )
