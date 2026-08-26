"""Concrete awsiot Microwave — translates MQTT state to the Microwave ABC."""

import logging
from typing import Any, override

from ..microwave import (
    HoodFanSpeed,
    HoodLightColor,
    HoodLightLevel,
    MicrowaveCavityState,
    MicrowaveDoorStatus,
    Recipe,
)
from ..microwave import (
    Microwave as MicrowaveABC,
)
from ..types import ApplianceInfo
from .appliance import Appliance, gated_set
from .capabilities import MicrowaveCapabilityProfile, MicrowaveRecipeOptions
from .mqttclient import MqttClient

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
    def __init__(
        self,
        mqttclient: MqttClient,
        appliance_info: ApplianceInfo,
        capability_profile: MicrowaveCapabilityProfile,
    ):
        super().__init__(mqttclient, appliance_info)
        self.capability_profile = capability_profile

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
        self._send_command("set", {"addressee": "primaryCavity", "cavityLight": on})
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
        return self.capability_profile.supports_hood_fan

    @override
    def supports_hood_light_level(self) -> bool:
        return self.capability_profile.supports_hood_light_level

    @override
    def supports_hood_light_color(self) -> bool:
        return self.capability_profile.supports_hood_light_color

    @override
    def supports_quiet_mode(self) -> bool:
        return self.capability_profile.supports_quiet_mode

    @override
    def supports_control_lock(self) -> bool:
        return self.capability_profile.supports_control_lock

    @override
    def supports_sabbath_mode(self) -> bool:
        return self.capability_profile.supports_sabbath_mode

    @override
    @gated_set(supports_hood_fan, "hood fan")
    async def set_hood_fan_speed(self, speed: HoodFanSpeed) -> bool:
        self._send_command("set", {"addressee": "hoodFan", "value": speed.value})
        return True

    @override
    @gated_set(supports_hood_light_level, "hood light")
    async def set_hood_light_level(self, level: HoodLightLevel) -> bool:
        self._send_command("set", {"addressee": "hoodLight", "value": level.value})
        return True

    @override
    @gated_set(supports_hood_light_color, "hood light color control")
    async def set_hood_light_color(self, color: HoodLightColor) -> bool:
        self._send_command("set", {"addressee": "hoodLightColor", "value": color.value})
        return True

    @override
    @gated_set(supports_control_lock, "control lock")
    async def set_control_locked(self, on: bool) -> bool:
        self._send_command("set", {"addressee": "hmiControlLockout", "value": on})
        return True

    @override
    @gated_set(supports_quiet_mode, "quiet mode")
    async def set_quiet_mode(self, on: bool) -> bool:
        self._send_command("set", {"addressee": "quietMode", "value": on})
        return True

    @override
    @gated_set(supports_sabbath_mode, "sabbath mode")
    async def set_sabbath_mode(self, on: bool) -> bool:
        self._send_command("set", {"addressee": "sabbathMode", "value": on})
        return True

    def get_recipe_options(self, recipe: Recipe) -> MicrowaveRecipeOptions | None:
        """Editable ranges for `recipe` on this model, or None if unsupported."""
        return self.capability_profile.recipes.get(recipe.value)

    @override
    async def set_cook(
        self,
        recipe: Recipe,
        duration_seconds: int,
        power_level: int | None = None,
    ) -> bool:
        options = self.get_recipe_options(recipe)
        if options is None:
            raise ValueError(f"recipe {recipe.value!r} is not supported by {self.said}")

        cook_time = options.cook_time
        if not cook_time.contains(duration_seconds):
            raise ValueError(
                f"duration_seconds must be {cook_time.min}-{cook_time.max} s "
                f"in steps of {cook_time.step} for recipe {recipe.value!r}"
            )

        payload: dict[str, Any] = {
            "addressee": "primaryCavity",
            "recipeID": recipe.value,
            "cookTimer": {"command": "run", "time": duration_seconds},
        }
        if options.power_level is not None:
            if power_level is None:
                raise ValueError(f"recipe {recipe.value!r} requires power_level")
            if not options.power_level.contains(power_level):
                raise ValueError(
                    f"power_level must be {options.power_level.min}-"
                    f"{options.power_level.max} in steps of "
                    f"{options.power_level.step} for recipe {recipe.value!r}"
                )
            payload["mwoPowerLevel"] = float(power_level)
        elif power_level is not None:
            fixed = options.fixed_power_level
            raise ValueError(
                f"recipe {recipe.value!r} has a fixed power level"
                + (f" of {fixed}" if fixed is not None else "")
                + "; omit power_level"
            )

        if not self.get_remote_start_enabled():
            LOGGER.warning(
                "Remote start not enabled on %s — enable on the physical panel",
                self.said,
            )
            return False
        self._send_command("run", payload)
        return True

    @override
    async def stop_cook(self) -> bool:
        self._send_command("cancel", {"addressee": "primaryCavity"})
        return True
