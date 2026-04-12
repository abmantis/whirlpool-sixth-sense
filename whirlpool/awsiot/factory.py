"""Appliance class factory driven by CapabilityProfile matchers."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .matchers import Matcher

if TYPE_CHECKING:
    from ..types import ApplianceInfo
    from .appliance import Appliance
    from .capabilities import CapabilityProfile

LOGGER = logging.getLogger(__name__)


@dataclass
class Registration:
    cls: type
    matcher: Matcher
    priority: int
    order: int  # insertion order, used for deterministic tie-break


class ApplianceFactory:
    def __init__(self) -> None:
        self._registrations: list[Registration] = []
        self._counter: int = 0

    def register(
        self,
        cls: type,
        matcher: Matcher,
        priority: int = 0,
    ) -> None:
        self._registrations.append(
            Registration(
                cls=cls, matcher=matcher, priority=priority, order=self._counter
            )
        )
        self._counter += 1

    def build(
        self,
        mqtt: Any,
        profile: CapabilityProfile,
        thing: dict[str, Any],
        appliance_info: ApplianceInfo,
    ) -> Appliance | None:
        matching: list[Registration] = [
            r for r in self._registrations if r.matcher(profile, thing)
        ]
        if not matching:
            return None

        matching.sort(key=lambda r: (-r.priority, r.order))
        top = matching[0]

        if len(matching) > 1 and matching[1].priority == top.priority:
            LOGGER.warning(
                "Capability %s matched multiple classes at priority %d; tie broken"
                " by registration order. First-registered=%s; others=%s",
                profile.part_number,
                top.priority,
                top.cls.__name__,
                [r.cls.__name__ for r in matching[1:] if r.priority == top.priority],
            )

        return top.cls(mqtt, appliance_info, profile)


DEFAULT_FACTORY = ApplianceFactory()


def register_appliance(
    matcher: Matcher,
    priority: int = 0,
    factory: ApplianceFactory | None = None,
) -> Callable[[type], type]:
    """Decorator for subclasses to self-register at import time."""

    target_factory = factory if factory is not None else DEFAULT_FACTORY

    def decorate(cls: type) -> type:
        target_factory.register(cls, matcher=matcher, priority=priority)
        return cls

    return decorate
