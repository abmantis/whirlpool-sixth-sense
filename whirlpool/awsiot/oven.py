import logging
import math
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

LOGGER = logging.getLogger(__name__)


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
    """AWS IoT oven implementation for the existing base Oven interface."""

    _VALIDATED_COMMAND_CAPABILITIES: ClassVar[set[str]] = {"W11779688"}

    _RECIPE_BY_MODE: ClassVar[dict[CookMode, str]] = {
        CookMode.Bake: "bake",
        CookMode.ConvectBake: "convectBake",
        CookMode.Broil: "broil",
        CookMode.ConvectBroil: "convectBroil",
        CookMode.ConvectRoast: "convectRoast",
        CookMode.KeepWarm: "keepWarm",
        CookMode.AirFry: "airFry",
    }
    _TARGET_RANGES: ClassVar[dict[CookMode, tuple[float, float]]] = {
        CookMode.Bake: (76.7, 288),
        CookMode.ConvectBake: (76.7, 288),
        CookMode.Broil: (232.2, 288),
        CookMode.ConvectBroil: (232, 288),
        CookMode.ConvectRoast: (76.7, 288),
        CookMode.KeepWarm: (65.6, 93.5),
        CookMode.AirFry: (76.7, 288),
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
        capabilities = raw_capabilities or {}
        self._capability_part_number = capabilities.get("partNumber")
        self._supports_cook_control = (
            self._capability_part_number in self._VALIDATED_COMMAND_CAPABILITIES
        )

        cavities = capabilities.get("cavities")
        self._cavity_names: list[str] = []
        if isinstance(cavities, dict):
            self._cavity_names = [
                name
                for name, metadata in cavities.items()
                if isinstance(metadata, dict) and metadata.get("cavityType") == "oven"
            ]

    def _cavity_name(self, cavity: Cavity) -> str | None:
        index = 0 if cavity is Cavity.Upper else 1
        return self._cavity_names[index] if index < len(self._cavity_names) else None

    def _warn_unsupported_command_profile(self) -> None:
        LOGGER.warning(
            "Model %s capability %s has no validated AWS oven command support",
            self.said,
            self._capability_part_number,
        )

    def _warn_missing_cavity(self, cavity: Cavity) -> None:
        LOGGER.warning("Model %s has no %s oven cavity", self.said, cavity.name.lower())

    @override
    def get_meat_probe_status(self, cavity: Cavity = Cavity.Upper) -> bool | None:
        # No real W11779688 state capture has established the AWS state key yet.
        return None

    @override
    def get_door_opened(self, cavity: Cavity = Cavity.Upper) -> bool | None:
        name = self._cavity_name(cavity)
        if name is None:
            return None
        value = self._get_path_str(name, "doorStatus")
        if value == "open":
            return True
        if value == "closed":
            return False
        return None

    @override
    def get_display_brightness_percent(self) -> int | None:
        return None

    @override
    async def set_display_brightness_percent(self, pct: int) -> bool:
        return False

    @override
    def get_cook_time(self, cavity: Cavity = Cavity.Upper) -> int | None:
        name = self._cavity_name(cavity)
        if name is None:
            return None
        return self._get_path_int(name, "cookTimer", "time")

    @override
    def get_control_locked(self) -> bool | None:
        return None

    @override
    async def set_control_locked(self, on: bool) -> bool:
        return False

    @override
    def get_light(self, cavity: Cavity = Cavity.Upper) -> bool | None:
        name = self._cavity_name(cavity)
        if name is None:
            return None
        return self._get_path_bool(name, "cavityLight")

    @override
    async def set_light(self, on: bool, cavity: Cavity = Cavity.Upper) -> bool:
        if not self._supports_cook_control:
            self._warn_unsupported_command_profile()
            return False
        name = self._cavity_name(cavity)
        if name is None:
            self._warn_missing_cavity(cavity)
            return False
        await self._send_command("set", {"addressee": name, "cavityLight": on})
        return True

    @override
    def get_temp(self, cavity: Cavity = Cavity.Upper) -> float | None:
        name = self._cavity_name(cavity)
        if name is None:
            return None
        value = self._get_path_float(name, "ovenDisplayTemperature")
        return value if value not in {None, 0} else None

    @override
    def get_target_temp(self, cavity: Cavity = Cavity.Upper) -> float | None:
        name = self._cavity_name(cavity)
        if name is None:
            return None
        value = self._get_path_float(name, "targetTemperature")
        return value if value not in {None, 0} else None

    @override
    def get_cavity_state(self, cavity: Cavity = Cavity.Upper) -> CavityState | None:
        name = self._cavity_name(cavity)
        if name is None:
            return None
        value = self._get_path_str(name, "cavityState")
        if value is None:
            return None
        return {
            "idle": CavityState.Standby,
            "preheating": CavityState.Preheating,
            "cooking": CavityState.Cooking,
        }.get(value)

    @override
    def get_oven_cavity_exists(self, cavity: Cavity) -> bool:
        return self._cavity_name(cavity) is not None

    @override
    def get_kitchen_timer(self, timer_id: int = 1) -> KitchenTimer:
        return _UnavailableTimer()

    @override
    def get_cook_mode(self, cavity: Cavity = Cavity.Upper) -> CookMode | None:
        name = self._cavity_name(cavity)
        if name is None:
            return None
        value = self._get_path_str(name, "recipeId")
        if value is None:
            return None
        return {
            "": CookMode.Standby,
            "standby": CookMode.Standby,
            "bake": CookMode.Bake,
            "convectBake": CookMode.ConvectBake,
            "broil": CookMode.Broil,
            "convectBroil": CookMode.ConvectBroil,
            "convectRoast": CookMode.ConvectRoast,
            "keepWarm": CookMode.KeepWarm,
            "airFry": CookMode.AirFry,
        }.get(value)

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
        if rapid_preheat is not None:
            raise ValueError("rapid_preheat is not supported by the AWS oven backend")
        if meat_probe_target_temp is not None:
            raise ValueError(
                "meat_probe_target_temp is not supported by the AWS oven backend"
            )
        if delay_cook is not None:
            raise ValueError("delay_cook is not supported by the AWS oven backend")
        if operation_type is not CookOperation.Start:
            raise ValueError(
                "operation_type values other than Start are not supported by "
                "the AWS oven backend"
            )

        if not self._supports_cook_control:
            self._warn_unsupported_command_profile()
            return False

        name = self._cavity_name(cavity)
        if name is None:
            self._warn_missing_cavity(cavity)
            return False

        recipe = self._RECIPE_BY_MODE.get(mode)
        if recipe is None:
            raise ValueError(f"Unsupported cook mode: {mode}")

        if not math.isfinite(target_temp):
            raise ValueError("Target temperature must be finite")
        minimum, maximum = self._TARGET_RANGES[mode]
        if not minimum <= target_temp <= maximum:
            raise ValueError(
                f"Target temperature must be between {minimum} and {maximum} C"
            )

        level_values = self._LEVEL_VALUES.get(mode)
        if level_values is not None:
            target_temp = min(level_values, key=lambda value: abs(value - target_temp))

        if self._get_path_bool("remoteStartEnable") is not True:
            LOGGER.warning(
                "Remote start is disabled for model %s; enable it at the appliance",
                self.said,
            )
            return False

        await self._send_command(
            "run",
            {
                "addressee": name,
                "recipeID": recipe,
                "targetTemperature": target_temp,
            },
        )
        return True

    @override
    async def stop_cook(self, cavity: Cavity = Cavity.Upper) -> bool:
        if not self._supports_cook_control:
            self._warn_unsupported_command_profile()
            return False

        name = self._cavity_name(cavity)
        if name is None:
            self._warn_missing_cavity(cavity)
            return False

        payload: dict[str, Any] = {"addressee": name}
        session_id = self._get_path_str(name, "sessionId")
        if session_id:
            payload["sessionId"] = session_id

        await self._send_command("cancel", payload)
        return True

    @override
    def get_sabbath_mode(self) -> bool | None:
        return None

    @override
    async def set_sabbath_mode(self, on: bool) -> bool:
        return False
