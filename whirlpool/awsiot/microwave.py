"""Concrete awsiot Microwave — translates MQTT state to the Microwave ABC."""

import logging
from typing import Any, override

from ..microwave import (
    HoodFanSpeed,
    HoodLightColor,
    HoodLightLevel,
    MicrowaveCavityState,
    MicrowaveDoorStatus,
)
from ..microwave import (
    Microwave as MicrowaveABC,
)
from .appliance import Appliance

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

_HOOD_FAN_MAP: dict[str, HoodFanSpeed] = {
    "off": HoodFanSpeed.Off,
    "low": HoodFanSpeed.Low,
    "med": HoodFanSpeed.Medium,
    "high": HoodFanSpeed.High,
    "boost": HoodFanSpeed.Boost,
}
_HOOD_LIGHT_MAP: dict[str, HoodLightLevel] = {
    "off": HoodLightLevel.Off,
    "low": HoodLightLevel.Low,
    "med": HoodLightLevel.Medium,
    "high": HoodLightLevel.High,
}
_HOOD_LIGHT_COLOR_MAP: dict[str, HoodLightColor] = {
    "warmWhite": HoodLightColor.WarmWhite,
    "naturalWhite": HoodLightColor.NaturalWhite,
    "coolWhite": HoodLightColor.CoolWhite,
}


class Microwave(MicrowaveABC, Appliance):
    @override
    def get_cavity_state(self) -> MicrowaveCavityState | None:
        raw = self._get_path_str("primaryCavity", "cavityState")
        return _CAVITY_STATE_MAP.get(raw) if raw is not None else None

    @override
    def get_door_status(self) -> MicrowaveDoorStatus | None:
        raw = self._get_path_str("primaryCavity", "doorStatus")
        return _DOOR_STATUS_MAP.get(raw) if raw is not None else None

    @override
    def get_door_locked(self) -> bool | None:
        value = self._get_path("primaryCavity", "doorLockStatus")
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            if value == "locked":
                return True
            if value == "unlocked":
                return False
        return None

    @override
    def get_cavity_light(self) -> bool | None:
        return self._get_path_bool("primaryCavity", "cavityLight")

    @override
    async def set_cavity_light(self, on: bool) -> bool:
        self._send_command(
            "set", {"addressee": "primaryCavity", "cavityLight": on}
        )
        return True

    @override
    def get_display_temperature(self) -> float | None:
        return self._get_path_float("primaryCavity", "ovenDisplayTemperature")

    @override
    def get_display_temperature_unit(self) -> str | None:
        raw = self._get_path_str("temperatureUnit")
        if raw is None:
            return None
        normalized = raw.strip().lower()
        if normalized in {"f", "fahrenheit"}:
            return "F"
        if normalized in {"c", "celsius"}:
            return "C"
        return None

    @override
    def get_turntable_enabled(self) -> bool | None:
        raw = self._get_path_str("primaryCavity", "turnTable")
        if raw == "on":
            return True
        if raw == "off":
            return False
        return None

    @override
    def get_active_recipe_id(self) -> str | None:
        raw = self._get_path_str("primaryCavity", "recipeId")
        return raw if raw else None

    @override
    def get_recipe_execution_state(self) -> str | None:
        return self._get_path_str("primaryCavity", "recipeExecutionState")

    @override
    def get_mwo_power_level(self) -> int | None:
        return self._get_path_int("primaryCavity", "mwoPowerLevel")

    @override
    def get_cook_timer_state(self) -> str | None:
        return self._get_path_str("primaryCavity", "cookTimer", "state")

    @override
    def get_cook_timer_total_seconds(self) -> int | None:
        return self._get_path_int("primaryCavity", "cookTimer", "time")

    @override
    def get_cook_timer_time_complete(self) -> int | None:
        return self._get_path_int("primaryCavity", "cookTimer", "timeComplete")

    @override
    def get_hood_fan_speed(self) -> HoodFanSpeed | None:
        raw = self._get_path_str("hoodFan", "userFanSpeed")
        return _HOOD_FAN_MAP.get(raw) if raw is not None else None

    @override
    def get_hood_light_level(self) -> HoodLightLevel | None:
        raw = self._get_path_str("hoodLight")
        return _HOOD_LIGHT_MAP.get(raw) if raw is not None else None

    @override
    def get_hood_light_color(self) -> HoodLightColor | None:
        raw = self._get_path_str("hoodLightColor")
        return _HOOD_LIGHT_COLOR_MAP.get(raw) if raw is not None else None

    @override
    def get_remote_start_enabled(self) -> bool | None:
        return self._get_path_bool("remoteStartEnable")

    @override
    def get_control_locked(self) -> bool | None:
        return self._get_path_bool("hmiControlLockout")

    @override
    def get_quiet_mode(self) -> bool | None:
        return self._get_path_bool("quietMode")

    @override
    def get_sabbath_mode(self) -> bool | None:
        return self._get_path_bool("sabbathMode")

    @override
    def supports_hood_fan(self) -> bool:
        return self.capability_profile.has_section("hoodFan")

    @override
    def supports_hood_light_level(self) -> bool:
        return self.capability_profile.has_section("hoodLight")

    @override
    def supports_hood_light_color(self) -> bool:
        return self.capability_profile.has_section("hoodLightColor")

    @override
    def supports_quiet_mode(self) -> bool:
        return self.capability_profile.has_flag("quietMode")

    @override
    def supports_control_lock(self) -> bool:
        return self.capability_profile.has_flag("supportsHmiControlLockout")

    @override
    def supports_sabbath_mode(self) -> bool:
        return self.capability_profile.sabbath_recipes_present

    async def _set_gated(
        self, supported: bool, addressee: str, value: Any, label: str
    ) -> bool:
        if not supported:
            LOGGER.warning("Model %s has no %s", self.said, label)
            return False
        self._send_command("set", {"addressee": addressee, "value": value})
        return True

    @override
    async def set_hood_fan_speed(self, speed: HoodFanSpeed) -> bool:
        return await self._set_gated(
            self.supports_hood_fan(), "hoodFan", speed.value, "hood fan"
        )

    @override
    async def set_hood_light_level(self, level: HoodLightLevel) -> bool:
        return await self._set_gated(
            self.supports_hood_light_level(), "hoodLight", level.value, "hood light"
        )

    @override
    async def set_hood_light_color(self, color: HoodLightColor) -> bool:
        return await self._set_gated(
            self.supports_hood_light_color(),
            "hoodLightColor",
            color.value,
            "hood light color control",
        )

    @override
    async def set_control_locked(self, on: bool) -> bool:
        return await self._set_gated(
            self.supports_control_lock(), "hmiControlLockout", on, "control lock"
        )

    @override
    async def set_quiet_mode(self, on: bool) -> bool:
        return await self._set_gated(
            self.supports_quiet_mode(), "quietMode", on, "quiet mode"
        )

    @override
    async def set_sabbath_mode(self, on: bool) -> bool:
        return await self._set_gated(
            self.supports_sabbath_mode(), "sabbathMode", on, "sabbath mode"
        )
