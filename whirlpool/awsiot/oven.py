import asyncio
import time
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
        CookMode.SteamBake: "steamBake",
        CookMode.FreshPizza: "freshPizza",
        CookMode.Proof: "proof",
        CookMode.SlowCook: "slowCook",
        CookMode.ConvectSlowRoast4Hour: "convectSlowRoastLow",
        CookMode.ConvectSlowRoast8Hour: "convectSlowRoastMedium",
        CookMode.ConvectSlowRoast12Hour: "convectSlowRoastHigh",
    }
    _TARGET_RANGES: ClassVar[dict[CookMode, tuple[float, float, float]]] = {
        CookMode.Bake: (76.7, 288, 176.7),
        CookMode.ConvectBake: (76.7, 288, 162.8),
        CookMode.Broil: (232.2, 288, 288),
        CookMode.ConvectBroil: (232, 288, 288),
        CookMode.ConvectRoast: (76.7, 288, 176.7),
        CookMode.KeepWarm: (65.6, 93.5, 76.7),
        CookMode.AirFry: (76.7, 288, 204.4),
        CookMode.SteamBake: (76.7, 288, 162.8),
        CookMode.FreshPizza: (232, 288, 288),
        CookMode.Proof: (32.2, 37.7, 32.2),
        CookMode.SlowCook: (82, 148.9, 121.1),
        CookMode.ConvectSlowRoast4Hour: (126.7, 140.6, 135),
        CookMode.ConvectSlowRoast8Hour: (98.9, 112.8, 107.2),
        CookMode.ConvectSlowRoast12Hour: (87.8, 98.9, 93.3),
    }
    _LEVEL_VALUES: ClassVar[dict[CookMode, tuple[float, ...]]] = {
        CookMode.Broil: (232.2, 260, 288),
        CookMode.ConvectBroil: (232, 260, 288),
        CookMode.FreshPizza: (232, 260, 288),
        CookMode.Proof: (32.2, 37.7),
    }
    _NO_DELAY_MODES: ClassVar[set[CookMode]] = {CookMode.FreshPizza}

    def __init__(
        self,
        mqttclient: MqttClient,
        appliance_info: ApplianceInfo,
        raw_capabilities: dict[str, Any] | None = None,
    ):
        super().__init__(mqttclient, appliance_info)
        self.raw_capabilities = raw_capabilities or {}
        self.supports_cook_control = (
            self.raw_capabilities.get("partNumber") in self._VALIDATED_COOK_CAPABILITIES
        )
        cavities = self.raw_capabilities.get("cavities", {})
        self._cavity_names = list(cavities) if isinstance(cavities, dict) else []
        self._staged_modes = {
            Cavity.Upper: CookMode.Bake,
            Cavity.Lower: CookMode.Bake,
        }
        self._staged_temperatures = {
            Cavity.Upper: 176.66667,
            Cavity.Lower: 176.66667,
        }
        self._staged_delay_seconds = {Cavity.Upper: 0, Cavity.Lower: 0}
        self._pending_power: dict[Cavity, tuple[bool, float]] = {}

    async def _refresh_after_command(self) -> None:
        for delay in (1, 3, 6):
            await asyncio.sleep(delay)
            await self._send_command("getState")

    def _schedule_state_refresh(self) -> None:
        asyncio.create_task(self._refresh_after_command())

    async def request_state(self) -> None:
        await self._send_command("getState")

    def update_online(self, online: bool) -> None:
        # The validated W11779688 profile can emit a disconnected presence
        # event while continuing to publish state and accept commands.
        if online or not self.supports_cook_control:
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
            "steambake": CookMode.SteamBake,
            "freshpizza": CookMode.FreshPizza,
            "proof": CookMode.Proof,
            "slowcook": CookMode.SlowCook,
            "convectslowroastlow": CookMode.ConvectSlowRoast4Hour,
            "convectslowroastmedium": CookMode.ConvectSlowRoast8Hour,
            "convectslowroasthigh": CookMode.ConvectSlowRoast12Hour,
        }
        if isinstance(value, str):
            return mapping.get(value.replace("_", "").replace("-", "").lower())
        try:
            return CookMode(value)
        except TypeError, ValueError:
            return None

    def get_configured_cook_mode(self, cavity: Cavity) -> CookMode:
        active = self.get_cook_mode(cavity)
        if active is not None and active is not CookMode.Standby:
            return active
        return self._staged_modes[cavity]

    def get_configured_target_temp(self, cavity: Cavity) -> float:
        active = self.get_target_temp(cavity)
        if active is not None and active != 0:
            return active
        return self._staged_temperatures[cavity]

    def stage_cook_mode(self, mode: CookMode, cavity: Cavity) -> None:
        if mode is CookMode.Standby:
            raise ValueError("Standby is not a startable cook mode")
        if mode not in self._RECIPE_BY_MODE:
            raise ValueError(f"Unsupported cook mode: {mode}")
        self._staged_modes[cavity] = mode
        minimum, maximum, default = self._TARGET_RANGES[mode]
        if not minimum <= self._staged_temperatures[cavity] <= maximum:
            self._staged_temperatures[cavity] = default
        for callback in self._attr_changed:
            callback()

    def get_target_range(self, cavity: Cavity) -> tuple[float, float]:
        mode = self.get_configured_cook_mode(cavity)
        minimum, maximum, _default = self._TARGET_RANGES[mode]
        return minimum, maximum

    def _level_value(self, mode: CookMode, target_temp: float) -> float:
        values = self._LEVEL_VALUES.get(mode)
        if values is None:
            return target_temp
        return min(values, key=lambda value: abs(value - target_temp))

    def stage_target_temp(self, target_temp: float, cavity: Cavity) -> None:
        target_temp = self._level_value(
            self.get_configured_cook_mode(cavity), target_temp
        )
        minimum, maximum = self.get_target_range(cavity)
        if not minimum <= target_temp <= maximum:
            raise ValueError(
                f"Target temperature must be between {minimum} and {maximum} C"
            )
        self._staged_temperatures[cavity] = target_temp

    def get_delay_start_minutes(self, cavity: Cavity) -> int:
        return self._staged_delay_seconds[cavity] // 60

    def stage_delay_start_minutes(self, minutes: int, cavity: Cavity) -> None:
        if minutes != 0 and (not 15 <= minutes <= 720 or minutes % 15):
            raise ValueError("Delay must be 0 or 15-720 minutes in 15-minute steps")
        self._staged_delay_seconds[cavity] = minutes * 60

    async def set_target_temp(self, target_temp: float, cavity: Cavity) -> bool:
        self.stage_target_temp(target_temp, cavity)
        state = self.get_cavity_state(cavity)
        if state in {None, CavityState.Standby, CavityState.NotPresent}:
            return True

        payload: dict[str, Any] = {
            "addressee": self._cavity_name(cavity),
            "targetTemperature": self._staged_temperatures[cavity],
        }
        session_id = self._cavity_value(cavity, "sessionId")
        if isinstance(session_id, str) and session_id:
            payload["sessionId"] = session_id
        await self._send_command("set", payload)
        self._schedule_state_refresh()
        return True

    async def start_staged_cook(self, cavity: Cavity) -> bool:
        return await self.set_cook(
            self._staged_temperatures[cavity], self._staged_modes[cavity], cavity
        )

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
        if not self.supports_cook_control:
            return False

        recipe = self._RECIPE_BY_MODE.get(mode)
        if recipe is None:
            raise ValueError(f"Unsupported cook mode: {mode}")
        target_temp = self._level_value(mode, target_temp)
        minimum, maximum = self._TARGET_RANGES[mode][:2]
        if not minimum <= target_temp <= maximum:
            raise ValueError(
                f"Target temperature must be between {minimum} and {maximum} C"
            )

        delay_seconds = self._staged_delay_seconds[cavity]
        if delay_seconds and mode in self._NO_DELAY_MODES:
            raise ValueError(f"{recipe} does not support a delayed start")
        if _first(self._data_dict, ("remoteStartEnable",)) is not True:
            return False

        self._staged_modes[cavity] = mode
        self._staged_temperatures[cavity] = target_temp
        payload: dict[str, Any] = {
            "addressee": self._cavity_name(cavity),
            "recipeID": recipe,
            "targetTemperature": target_temp,
        }
        if delay_seconds:
            payload["delayTimer"] = {"command": "run", "time": delay_seconds}
        self._pending_power[cavity] = (True, time.monotonic() + 12)
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
        self._pending_power[cavity] = (False, time.monotonic() + 12)
        self._schedule_state_refresh()
        return True

    def get_power_state(self, cavity: Cavity) -> bool | None:
        state = self.get_cavity_state(cavity)
        actual = (
            None
            if state is None
            else state not in {CavityState.Standby, CavityState.NotPresent}
        )
        pending = self._pending_power.get(cavity)
        if pending is None:
            return actual
        desired, expires = pending
        if actual == desired or time.monotonic() >= expires:
            self._pending_power.pop(cavity, None)
            return actual
        return desired

    @override
    def get_sabbath_mode(self) -> bool | None:
        value = _first(self._data_dict, ("sabbathMode",))
        return value if isinstance(value, bool) else None

    @override
    async def set_sabbath_mode(self, on: bool) -> bool:
        return False
