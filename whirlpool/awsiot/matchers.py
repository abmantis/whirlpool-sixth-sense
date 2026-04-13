"""Matcher helpers used by the ApplianceFactory for class routing.

Each helper returns a callable with the signature
`(CapabilityProfile, thing_dict) -> bool`. Subclasses combine matchers
through `all_of`, `any_of`, `not_` to declare when they should fire.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .capabilities import CapabilityProfile

Matcher = Callable[[CapabilityProfile, dict[str, Any]], bool]


def has_feature(name: str) -> Matcher:
    def _match(profile: CapabilityProfile, _thing: dict[str, Any]) -> bool:
        return profile.has_feature(name)

    return _match


def has_addressee(name: str) -> Matcher:
    def _match(profile: CapabilityProfile, _thing: dict[str, Any]) -> bool:
        return profile.has_addressee(name)

    return _match


def has_command(addressee: str, command: str) -> Matcher:
    def _match(profile: CapabilityProfile, _thing: dict[str, Any]) -> bool:
        return profile.supports_command(addressee, command)

    return _match


def model_prefix(prefix: str) -> Matcher:
    def _match(_profile: CapabilityProfile, thing: dict[str, Any]) -> bool:
        model = thing.get("thingTypeName", "")
        return isinstance(model, str) and model.startswith(prefix)

    return _match


def thing_category(name: str) -> Matcher:
    target = name.lower()

    def _match(_profile: CapabilityProfile, thing: dict[str, Any]) -> bool:
        attrs = thing.get("attributes") or {}
        category = str(attrs.get("Category", "")).lower()
        return category == target

    return _match


def all_of(*matchers: Matcher) -> Matcher:
    def _match(profile: CapabilityProfile, thing: dict[str, Any]) -> bool:
        return all(m(profile, thing) for m in matchers)

    return _match


def any_of(*matchers: Matcher) -> Matcher:
    def _match(profile: CapabilityProfile, thing: dict[str, Any]) -> bool:
        return any(m(profile, thing) for m in matchers)

    return _match


def not_(matcher: Matcher) -> Matcher:
    def _match(profile: CapabilityProfile, thing: dict[str, Any]) -> bool:
        return not matcher(profile, thing)

    return _match
