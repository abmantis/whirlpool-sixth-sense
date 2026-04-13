"""Concrete awsiot Microwave — translates MQTT state to MicrowaveABC."""

from __future__ import annotations

import logging
import time
from typing import override

from ..microwave import (
    HoodFanSpeed,
    HoodLightColor,
    HoodLightLevel,
    MicrowaveCavityState,
    MicrowaveDoorStatus,
    RecipeId,
)
from ..microwave import (
    Microwave as MicrowaveABC,
)
from .appliance import Appliance
from .factory import register_appliance
from .matchers import all_of, has_addressee, has_feature

LOGGER = logging.getLogger(__name__)

_CAVITY_STATE_MAP: dict[str, MicrowaveCavityState] = {
    "idle": MicrowaveCavityState.Idle,
    "cooking": MicrowaveCavityState.Cooking,
    "paused": MicrowaveCavityState.Paused,
    "completed": MicrowaveCavityState.Completed,
    "turningOff": MicrowaveCavityState.TurningOff,
}

_DOOR_STATUS_MAP: dict[str, MicrowaveDoorStatus] = {
    "open": MicrowaveDoorStatus.Open,
    "closed": MicrowaveDoorStatus.Closed,
}

_HOOD_FAN_MAP: dict[str, HoodFanSpeed] = {e.value: e for e in HoodFanSpeed}
_HOOD_LIGHT_MAP: dict[str, HoodLightLevel] = {e.value: e for e in HoodLightLevel}
_HOOD_LIGHT_COLOR_MAP: dict[str, HoodLightColor] = {
    e.value: e for e in HoodLightColor
}


@register_appliance(
    matcher=all_of(
        has_addressee("primaryCavity"),
        has_feature("microwaveOven"),
    ),
    priority=10,
)
class Microwave(Appliance, MicrowaveABC):
    # --- cavity state ----------------------------------------------------

    @override
    def get_cavity_state(self) -> MicrowaveCavityState:
        raw = self._get_path_str("primaryCavity.cavityState")
        if raw is None:
            return MicrowaveCavityState.Unknown
        return _CAVITY_STATE_MAP.get(raw, MicrowaveCavityState.Unknown)

    @override
    def get_door_status(self) -> MicrowaveDoorStatus:
        raw = self._get_path_str("primaryCavity.doorStatus")
        if raw is None:
            return MicrowaveDoorStatus.Unknown
        return _DOOR_STATUS_MAP.get(raw, MicrowaveDoorStatus.Unknown)

    @override
    def get_door_locked(self) -> bool | None:
        value = self._get_path("primaryCavity.doorLockStatus")
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value == "locked"
        return None

    @override
    def get_cavity_light(self) -> bool | None:
        return self._get_path_bool("primaryCavity.cavityLight")

    @override
    async def set_cavity_light(self, on: bool) -> bool:
        await self._send_command("primaryCavity", "set", cavityLight=on)
        return True

    @override
    def get_display_temperature(self) -> float | None:
        return self._get_path_float("primaryCavity.ovenDisplayTemperature")

    @override
    def get_display_temperature_unit(self) -> str | None:
        raw = self._get_path_str("temperatureUnit")
        if raw is None:
            return None
        return "F" if raw.lower().startswith("f") else "C"

    @override
    def get_turntable_enabled(self) -> bool | None:
        raw = self._get_path_str("primaryCavity.turnTable")
        if raw is None or raw == "":
            return None
        return raw == "on"

    # --- cook / timer ----------------------------------------------------

    @override
    def get_active_recipe_id(self) -> str | None:
        raw = self._get_path_str("primaryCavity.recipeId")
        return raw or None

    @override
    def get_recipe_execution_state(self) -> str | None:
        return self._get_path_str("primaryCavity.recipeExecutionState")

    @override
    def get_mwo_power_level(self) -> int | None:
        return self._get_path_int("primaryCavity.mwoPowerLevel")

    @override
    def get_cook_timer_state(self) -> str | None:
        return self._get_path_str("primaryCavity.cookTimer.state")

    @override
    def get_cook_timer_total_seconds(self) -> int | None:
        return self._get_path_int("primaryCavity.cookTimer.time")

    @override
    def get_cook_timer_remaining_seconds(self) -> int | None:
        time_complete = self._get_path_int("primaryCavity.cookTimer.timeComplete")
        if time_complete is None:
            return self._get_path_int("primaryCavity.cookTimer.time")
        remaining = time_complete - int(time.time())
        return max(0, remaining)

    @override
    async def start_cook(
        self,
        recipe: RecipeId,
        power_level: int,
        duration_seconds: int,
    ) -> bool:
        if not 1 <= power_level <= 100:
            raise ValueError("power_level must be between 1 and 100")
        if duration_seconds < 1:
            raise ValueError("duration_seconds must be >= 1")
        if not self.get_remote_start_enabled():
            LOGGER.warning(
                "Remote start is not enabled on %s — enable on the physical panel",
                self.said,
            )
            return False
        await self._send_command(
            "primaryCavity",
            "run",
            recipeID=recipe.value,
            mwoPowerLevel=float(power_level),
            cookTimer={"command": "start", "time": duration_seconds},
        )
        return True

    @override
    async def cancel_cook(self) -> bool:
        await self._send_command("primaryCavity", "cancel")
        return True

    # --- hood ------------------------------------------------------------

    @override
    def get_hood_fan_speed(self) -> HoodFanSpeed | None:
        raw = self._get_path_str("hoodFan.userFanSpeed")
        return _HOOD_FAN_MAP.get(raw) if raw else None

    @override
    async def set_hood_fan_speed(self, speed: HoodFanSpeed) -> bool:
        if not self._capability_profile.has_addressee("hoodFan"):
            LOGGER.warning("Model %s has no hood fan", self.said)
            return False
        await self._send_command("hoodFan", "set", value=speed.value)
        return True

    @override
    def get_hood_light_level(self) -> HoodLightLevel | None:
        raw = self._get_path_str("hoodLight")
        return _HOOD_LIGHT_MAP.get(raw) if raw else None

    @override
    async def set_hood_light_level(self, level: HoodLightLevel) -> bool:
        if not self._capability_profile.has_addressee("hoodLight"):
            LOGGER.warning("Model %s has no hood light", self.said)
            return False
        await self._send_command("hoodLight", "set", value=level.value)
        return True

    @override
    def get_hood_light_color(self) -> HoodLightColor | None:
        raw = self._get_path_str("hoodLightColor")
        return _HOOD_LIGHT_COLOR_MAP.get(raw) if raw else None

    @override
    async def set_hood_light_color(self, color: HoodLightColor) -> bool:
        if not self._capability_profile.has_addressee("hoodLightColor"):
            LOGGER.warning("Model %s has no hood light color control", self.said)
            return False
        await self._send_command("hoodLightColor", "set", value=color.value)
        return True

    # --- modes -----------------------------------------------------------

    @override
    def get_remote_start_enabled(self) -> bool | None:
        return self._get_path_bool("remoteStartEnable")

    # --- capability gates ------------------------------------------------
    # Per Android decompile (ComplementaryCommand.java) each of these
    # features is its own addressee with a generic `value` payload — the
    # cloud rejects the command (bouncing the device's IoT session) when
    # the model doesn't declare support.

    @property
    def supports_control_lock(self) -> bool:
        return (
            self._capability_profile.metadata.get("supportsHmiControlLockout")
            is True
        )

    @property
    def supports_quiet_mode(self) -> bool:
        return self._capability_profile.metadata.get("quietMode") is True

    @property
    def supports_sabbath_mode(self) -> bool:
        return (
            self._capability_profile.has_feature("sabbathMode")
            or self._capability_profile.metadata.get("sabbathMode") is True
        )

    @override
    def get_control_locked(self) -> bool | None:
        return self._get_path_bool("hmiControlLockout")

    @override
    async def set_control_locked(self, on: bool) -> bool:
        if not self.supports_control_lock:
            LOGGER.warning("Model %s does not support control lock", self.said)
            return False
        await self._send_command("hmiControlLockout", "set", value=on)
        return True

    @override
    def get_quiet_mode(self) -> bool | None:
        return self._get_path_bool("quietMode")

    @override
    async def set_quiet_mode(self, on: bool) -> bool:
        if not self.supports_quiet_mode:
            LOGGER.warning("Model %s does not support quiet mode", self.said)
            return False
        await self._send_command("quietMode", "set", value=on)
        return True

    @override
    def get_sabbath_mode(self) -> bool | None:
        return self._get_path_bool("sabbathMode")

    @override
    async def set_sabbath_mode(self, on: bool) -> bool:
        if not self.supports_sabbath_mode:
            LOGGER.warning("Model %s does not support sabbath mode", self.said)
            return False
        await self._send_command("sabbathMode", "set", value=on)
        return True
