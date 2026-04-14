"""Concrete awsiot Microwave — translates MQTT state to the Microwave ABC."""

from __future__ import annotations

import time
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


class Microwave(MicrowaveABC, Appliance):
    def _get_path(self, *path: str) -> Any:
        """Walk the state dict along `path`; return None if any step is missing."""
        value: Any = self._data_dict
        for key in path:
            if not isinstance(value, dict):
                return None
            value = value.get(key)
            if value is None:
                return None
        return value

    def _get_path_str(self, *path: str) -> str | None:
        value = self._get_path(*path)
        return value if isinstance(value, str) else None

    def _get_path_bool(self, *path: str) -> bool | None:
        value = self._get_path(*path)
        return value if isinstance(value, bool) else None

    def _get_path_int(self, *path: str) -> int | None:
        value = self._get_path(*path)
        if isinstance(value, bool):
            return None
        return int(value) if isinstance(value, (int, float)) else None

    def _get_path_float(self, *path: str) -> float | None:
        value = self._get_path(*path)
        if isinstance(value, bool):
            return None
        return float(value) if isinstance(value, (int, float)) else None

    @override
    def get_cavity_state(self) -> MicrowaveCavityState:
        raw = self._get_path_str("primaryCavity", "cavityState")
        if raw is None:
            return MicrowaveCavityState.Unknown
        return _CAVITY_STATE_MAP.get(raw, MicrowaveCavityState.Unknown)

    @override
    def get_door_status(self) -> MicrowaveDoorStatus:
        raw = self._get_path_str("primaryCavity", "doorStatus")
        if raw is None:
            return MicrowaveDoorStatus.Unknown
        return _DOOR_STATUS_MAP.get(raw, MicrowaveDoorStatus.Unknown)

    @override
    def get_door_locked(self) -> bool | None:
        value = self._get_path("primaryCavity", "doorLockStatus")
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value == "locked"
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
        return "F" if raw.lower().startswith("f") else "C"

    @override
    def get_turntable_enabled(self) -> bool | None:
        raw = self._get_path_str("primaryCavity", "turnTable")
        if raw is None or raw == "":
            return None
        return raw == "on"

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
    def get_cook_timer_remaining_seconds(self) -> int | None:
        time_complete = self._get_path_int(
            "primaryCavity", "cookTimer", "timeComplete"
        )
        if time_complete is not None:
            return max(0, time_complete - int(time.time()))
        return self.get_cook_timer_total_seconds()

    @override
    def get_hood_fan_speed(self) -> HoodFanSpeed | None:
        raw = self._get_path_str("hoodFan", "userFanSpeed")
        return _HOOD_FAN_MAP.get(raw) if raw else None

    @override
    def get_hood_light_level(self) -> HoodLightLevel | None:
        raw = self._get_path_str("hoodLight")
        return _HOOD_LIGHT_MAP.get(raw) if raw else None

    @override
    def get_hood_light_color(self) -> HoodLightColor | None:
        raw = self._get_path_str("hoodLightColor")
        return _HOOD_LIGHT_COLOR_MAP.get(raw) if raw else None

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
