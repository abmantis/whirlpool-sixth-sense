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
    def _get(self, *path: str) -> Any:
        """Walk the state dict along `path`; return None if any step is missing."""
        value: Any = self._data_dict
        for key in path:
            if not isinstance(value, dict):
                return None
            value = value.get(key)
            if value is None:
                return None
        return value

    @override
    def get_cavity_state(self) -> MicrowaveCavityState:
        raw = self._get("primaryCavity", "cavityState")
        if not isinstance(raw, str):
            return MicrowaveCavityState.Unknown
        return _CAVITY_STATE_MAP.get(raw, MicrowaveCavityState.Unknown)

    @override
    def get_door_status(self) -> MicrowaveDoorStatus:
        raw = self._get("primaryCavity", "doorStatus")
        if not isinstance(raw, str):
            return MicrowaveDoorStatus.Unknown
        return _DOOR_STATUS_MAP.get(raw, MicrowaveDoorStatus.Unknown)

    @override
    def get_door_locked(self) -> bool | None:
        value = self._get("primaryCavity", "doorLockStatus")
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value == "locked"
        return None

    @override
    def get_cavity_light(self) -> bool | None:
        value = self._get("primaryCavity", "cavityLight")
        return value if isinstance(value, bool) else None

    @override
    async def set_cavity_light(self, on: bool) -> bool:
        self._send_command(
            "set", {"addressee": "primaryCavity", "cavityLight": on}
        )
        return True

    @override
    def get_display_temperature(self) -> float | None:
        value = self._get("primaryCavity", "ovenDisplayTemperature")
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        return None

    @override
    def get_display_temperature_unit(self) -> str | None:
        raw = self._get("temperatureUnit")
        if not isinstance(raw, str):
            return None
        return "F" if raw.lower().startswith("f") else "C"

    @override
    def get_turntable_enabled(self) -> bool | None:
        raw = self._get("primaryCavity", "turnTable")
        if not isinstance(raw, str) or raw == "":
            return None
        return raw == "on"

    @override
    def get_active_recipe_id(self) -> str | None:
        raw = self._get("primaryCavity", "recipeId")
        return raw if isinstance(raw, str) and raw else None

    @override
    def get_recipe_execution_state(self) -> str | None:
        raw = self._get("primaryCavity", "recipeExecutionState")
        return raw if isinstance(raw, str) else None

    @override
    def get_mwo_power_level(self) -> int | None:
        value = self._get("primaryCavity", "mwoPowerLevel")
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return int(value)
        return None

    @override
    def get_cook_timer_state(self) -> str | None:
        raw = self._get("primaryCavity", "cookTimer", "state")
        return raw if isinstance(raw, str) else None

    @override
    def get_cook_timer_total_seconds(self) -> int | None:
        value = self._get("primaryCavity", "cookTimer", "time")
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return int(value)
        return None

    @override
    def get_cook_timer_remaining_seconds(self) -> int | None:
        time_complete = self._get("primaryCavity", "cookTimer", "timeComplete")
        if isinstance(time_complete, (int, float)) and not isinstance(
            time_complete, bool
        ):
            return max(0, int(time_complete) - int(time.time()))
        return self.get_cook_timer_total_seconds()

    @override
    def get_hood_fan_speed(self) -> HoodFanSpeed | None:
        raw = self._get("hoodFan", "userFanSpeed")
        return _HOOD_FAN_MAP.get(raw) if isinstance(raw, str) else None

    @override
    def get_hood_light_level(self) -> HoodLightLevel | None:
        raw = self._get("hoodLight")
        return _HOOD_LIGHT_MAP.get(raw) if isinstance(raw, str) else None

    @override
    def get_hood_light_color(self) -> HoodLightColor | None:
        raw = self._get("hoodLightColor")
        return _HOOD_LIGHT_COLOR_MAP.get(raw) if isinstance(raw, str) else None

    @override
    def get_remote_start_enabled(self) -> bool | None:
        value = self._get("remoteStartEnable")
        return value if isinstance(value, bool) else None

    @override
    def get_control_locked(self) -> bool | None:
        value = self._get("hmiControlLockout")
        return value if isinstance(value, bool) else None

    @override
    def get_quiet_mode(self) -> bool | None:
        value = self._get("quietMode")
        return value if isinstance(value, bool) else None

    @override
    def get_sabbath_mode(self) -> bool | None:
        value = self._get("sabbathMode")
        return value if isinstance(value, bool) else None
