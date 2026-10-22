import asyncio
from typing import Any, ClassVar, override

from ..oven import (
    Cavity,
    CavityState,
    CookMode,
    CookOperation,
    KitchenTimer,
    KitchenTimerOperations,
    KitchenTimerState,
)
from ..oven import Oven as BaseOven
from ..types import ApplianceInfo
from .appliance import Appliance
from .mqttclient import MqttClient


def _first(data: dict[str, Any], *paths: tuple[str, ...]) -> Any:
    """Return the first value found at one of several paths."""
    for path in paths:
        value: Any = data
        for key in path:
            if not isinstance(value, dict) or key not in value:
                break
            value = value[key]
        else:
            return value
    return None


class _UnavailableTimer(KitchenTimer):
    def get_total_time(self) -> int | None:
        return None

    def get_remaining_time(self) -> int | None:
        return None

    def get_state(self) -> KitchenTimerState | None:
        return None

    async def set_timer(
        self,
        timer_time: int,
        operation: KitchenTimerOperations = KitchenTimerOperations.Start,
    ) -> bool:
        return False

    async def cancel_timer(self) -> bool:
        return False


class Oven(BaseOven, Appliance):
    """AWS IoT oven implementation.

    The command mappings are based on the physically validated
    W11779688 capability profile.
    """

    _VALIDATED_COOK_CAPABILITIES: ClassVar[set[str]] = {"W11779688"}

    _RECIPE_BY_MODE: ClassVar[dict[CookMode, str]] = {
        CookMode.Bake: "bake",
        CookMode.ConvectBake: "convectBake",
        CookMode.Broil: "broil",
        CookMode.ConvectBroil: "convectBroil",
        CookMode.ConvectRoast: "convectRoast",
        CookMode.KeepWarm: "keepWarm",
        CookMode.AirFry: "airFry",
    }
    _TARGET_RANGES: ClassVar[dict[CookMode, tuple[float, float, float]]] = {
        CookMode.Bake: (76.7, 288, 176.7),
        CookMode.ConvectBake: (76.7, 288, 162.8),
        CookMode.Broil: (232.2, 288, 288),
        CookMode.ConvectBroil: (232, 288, 288),
        CookMode.ConvectRoast: (76.7, 288, 176.7),
        CookMode.KeepWarm: (65.6, 93.5, 76.7),
        CookMode.AirFry: (76.7, 288, 204.4),
    }
    _LEVEL_VALUES: ClassVar[dict[CookMode, tuple[float, ...]]] = {
        CookMode.Broil: (232.2, 260, 288),
        CookMode.ConvectBroil: (232, 260, 288),
    }

    def __init__(
        self,
        mqttclient: MqttClient,
        appliance_info: ApplianceInfo,
        raw_capabilities: dict[str, Any] | None = None,
    ):
        super().__init__(mqttclient, appliance_info)
        self.raw_capabilities = raw_capabilities or {}
        self._supports_cook_control = (
            self.raw_capabilities.get("partNumber") in self._VALIDATED_COOK_CAPABILITIES
        )
        cavities = self.raw_capabilities.get("cavities", {})
        self._cavity_names = list(cavities) if isinstance(cavities, dict) else []

    async def _refresh_after_command(self) -> None:
        for delay in (1, 3, 6):
            await asyncio.sleep(delay)
            await self._send_command("getState")

    def _schedule_state_refresh(self) -> None:
        asyncio.create_task(self._refresh_after_command())

    def update_online(self, online: bool) -> None:
        # The validated W11779688 profile can emit a disconnected presence
        # event while continuing to publish state and accept commands.
        if online or not self._supports_cook_control:
            super().update_online(online)

    def _cavity_name(self, cavity: Cavity) -> str:
        preferred = (
            ("upperCavity", "primaryCavity", "cavity1")
            if cavity is Cavity.Upper
            else ("lowerCavity", "secondaryCavity", "cavity2")
        )
        for name in preferred:
            if name in self._data_dict or name in self._cavity_names:
                return name
        index = 0 if cavity is Cavity.Upper else 1
        return (
            self._cavity_names[index]
            if index < len(self._cavity_names)
            else preferred[0]
        )

    def _cavity_value(self, cavity: Cavity, *keys: str) -> Any:
        name = self._cavity_name(cavity)
        return _first(self._data_dict, *((name, key) for key in keys))

    @override
    def get_meat_probe_status(self, cavity: Cavity = Cavity.Upper) -> bool | None:
        value = self._cavity_value(cavity, "meatProbeConnected", "meatProbeStatus")
        if isinstance(value, bool):
            return value
        return (
            value.lower() in {"connected", "inserted"}
            if isinstance(value, str)
            else None
        )

    @override
    def get_door_opened(self, cavity: Cavity = Cavity.Upper) -> bool | None:
        value = self._cavity_value(cavity, "doorStatus", "doorState", "doorOpen")
        if isinstance(value, bool):
            return value
        return value.lower() == "open" if isinstance(value, str) else None

    @override
    def get_display_brightness_percent(self) -> int | None:
        value = _first(
            self._data_dict, ("displayBrightness",), ("displayBrightnessPercent",)
        )
        return (
            int(value)
            if isinstance(value, (int, float)) and not isinstance(value, bool)
            else None
        )

    @override
    async def set_display_brightness_percent(self, pct: int) -> bool:
        return False

    @override
    def get_cook_time(self, cavity: Cavity = Cavity.Upper) -> int | None:
        value = self._cavity_value(cavity, "cookTime", "cookTimeRemaining")
        if isinstance(value, dict):
            value = value.get("time") or value.get("remaining")
        return (
            int(value)
            if isinstance(value, (int, float)) and not isinstance(value, bool)
            else None
        )

    @override
    def get_control_locked(self) -> bool | None:
        value = _first(self._data_dict, ("hmiControlLockout",), ("controlLock",))
        return value if isinstance(value, bool) else None

    @override
    async def set_control_locked(self, on: bool) -> bool:
        return False

    @override
    def get_light(self, cavity: Cavity = Cavity.Upper) -> bool | None:
        value = self._cavity_value(cavity, "cavityLight", "ovenLight", "light")
        if isinstance(value, bool):
            return value
        return value.lower() == "on" if isinstance(value, str) else None

    @override
    async def set_light(self, on: bool, cavity: Cavity = Cavity.Upper) -> bool:
        await self._send_command(
            "set", {"addressee": self._cavity_name(cavity), "cavityLight": on}
        )
        self._schedule_state_refresh()
        return True

    def _temperature(self, cavity: Cavity, *keys: str) -> float | None:
        value = self._cavity_value(cavity, *keys)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return None
        return float(value)

    @override
    def get_temp(self, cavity: Cavity = Cavity.Upper) -> float | None:
        return self._temperature(
            cavity, "ovenDisplayTemperature", "currentTemperature", "temperature"
        )

    @override
    def get_target_temp(self, cavity: Cavity = Cavity.Upper) -> float | None:
        return self._temperature(
            cavity, "targetTemperature", "setTemperature", "cookTemperature"
        )

    @override
    def get_cavity_state(self, cavity: Cavity = Cavity.Upper) -> CavityState | None:
        value = self._cavity_value(cavity, "cavityState", "ovenState", "state")
        mapping = {
            "idle": CavityState.Standby,
            "standby": CavityState.Standby,
            "preheating": CavityState.Preheating,
            "preheat": CavityState.Preheating,
            "cooking": CavityState.Cooking,
            "running": CavityState.Cooking,
        }
        if isinstance(value, str):
            return mapping.get(value.replace("_", "").lower())
        try:
            return CavityState(value)
        except TypeError, ValueError:
            return None

    @override
    def get_oven_cavity_exists(self, cavity: Cavity) -> bool:
        if cavity is Cavity.Upper:
            return bool(self._cavity_names) or any(
                key in self._data_dict
                for key in ("upperCavity", "primaryCavity", "cavity1")
            )
        return len(self._cavity_names) > 1 or any(
            key in self._data_dict
            for key in ("lowerCavity", "secondaryCavity", "cavity2")
        )

    @override
    def get_kitchen_timer(self, timer_id: int = 1) -> KitchenTimer:
        return _UnavailableTimer()

    @override
    def get_cook_mode(self, cavity: Cavity = Cavity.Upper) -> CookMode | None:
        value = self._cavity_value(cavity, "cookMode", "recipeId", "recipeID", "mode")
        mapping = {
            "standby": CookMode.Standby,
            "bake": CookMode.Bake,
            "convectbake": CookMode.ConvectBake,
            "convectionbake": CookMode.ConvectBake,
            "broil": CookMode.Broil,
            "convectbroil": CookMode.ConvectBroil,
            "convectroast": CookMode.ConvectRoast,
            "keepwarm": CookMode.KeepWarm,
            "airfry": CookMode.AirFry,
        }
        if isinstance(value, str):
            return mapping.get(value.replace("_", "").replace("-", "").lower())
        try:
            return CookMode(value)
        except TypeError, ValueError:
            return None

    @override
    async def set_cook(
        self,
        target_temp: float,
        mode: CookMode = CookMode.Bake,
        cavity: Cavity = Cavity.Upper,
        rapid_preheat: bool | None = None,
        meat_probe_target_temp: float | None = None,
        delay_cook: int | None = None,
        operation_type: CookOperation = CookOperation.Start,
    ) -> bool:
        if not self._supports_cook_control:
            return False

        recipe = self._RECIPE_BY_MODE.get(mode)
        if recipe is None:
            raise ValueError(f"Unsupported cook mode: {mode}")
        level_values = self._LEVEL_VALUES.get(mode)
        if level_values is not None:
            target_temp = min(level_values, key=lambda value: abs(value - target_temp))
        minimum, maximum = self._TARGET_RANGES[mode][:2]
        if not minimum <= target_temp <= maximum:
            raise ValueError(
                f"Target temperature must be between {minimum} and {maximum} C"
            )

        if _first(self._data_dict, ("remoteStartEnable",)) is not True:
            return False

        payload: dict[str, Any] = {
            "addressee": self._cavity_name(cavity),
            "recipeID": recipe,
            "targetTemperature": target_temp,
        }
        await self._send_command("run", payload)
        self._schedule_state_refresh()
        return True

    @override
    async def stop_cook(self, cavity: Cavity = Cavity.Upper) -> bool:
        payload: dict[str, Any] = {"addressee": self._cavity_name(cavity)}
        session_id = self._cavity_value(cavity, "sessionId")
        if isinstance(session_id, str) and session_id:
            payload["sessionId"] = session_id
        await self._send_command("cancel", payload)
        self._schedule_state_refresh()
        return True

    @override
    def get_sabbath_mode(self) -> bool | None:
        value = _first(self._data_dict, ("sabbathMode",))
        return value if isinstance(value, bool) else None

    @override
    async def set_sabbath_mode(self, on: bool) -> bool:
        return False
