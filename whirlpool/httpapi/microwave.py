"""Microwave on the HTTP (legacy) API.

Built-in microwaves such as the W9 MWO (``ddm_cooking_bi_mwo_*`` data models)
report the same attribute layout as the HTTP ovens, but with the ``Mwo_``
prefix instead of ``OvenUpperCavity_``. The status codes below were captured
on a real W9 MWO (DDM_COOKING_BI_MWO_SELF_CLEAN_STEAM_TOURMALINE_V2) while
starting, pausing (door opened), resuming and finishing a cycle. Recipes,
hood and quiet mode are not exposed by this API, so those parts of the
contract report unsupported.
"""

import logging
from typing import override

from ..microwave import (
    HoodFanSpeed,
    HoodLightColor,
    HoodLightLevel,
    MicrowaveCavityState,
    MicrowaveDoorStatus,
    Recipe,
)
from ..microwave import (
    Microwave as BaseMicrowave,
)
from .appliance import Appliance
from .oven import KitchenTimer

LOGGER = logging.getLogger(__name__)

ATTR_PREFIX = "Mwo_"

ATTR_CONTROL_LOCK = "Sys_OperationSetControlLock"
ATTR_SABBATH_MODE = "Sys_OperationSetSabbathModeEnabled"
ATTR_TEMP_UNITS = "Sys_DisplaySetTempUnits"

ATTR_STATUS_STATE = ATTR_PREFIX + "OperationStatusState"
ATTR_COOK_TIME_STATE = ATTR_PREFIX + "OperationStatusCookTimeState"
ATTR_DOOR_OPEN = ATTR_PREFIX + "OperationStatusDoorOpen"
ATTR_LIGHT = ATTR_PREFIX + "DisplaySetLightOn"
ATTR_DISPLAY_TEMP = ATTR_PREFIX + "DisplayStatusDisplayTemp"
ATTR_TURNTABLE = ATTR_PREFIX + "CycleSetTurntable"
ATTR_COOK_POWER_WATTS = ATTR_PREFIX + "CycleSetCookPowerWatts"
ATTR_COOK_TIME_SET = ATTR_PREFIX + "TimeSetCookTimeSet"
ATTR_COOK_TIME_REMAINING = ATTR_PREFIX + "TimeStatusCookTimeRemaining"
ATTR_COOK_TIME_ELAPSED = ATTR_PREFIX + "TimeStatusCycleTimeElapsed"
ATTR_ODOMETER = ATTR_PREFIX + "CycleStatusOdometer"
ATTR_SET_OPERATIONS = ATTR_PREFIX + "OperationSetOperations"

ATTRVAL_STATE_IDLE = "0"
ATTRVAL_STATE_PROGRAMMING = "2"  # cycle being set up, a few seconds before start
ATTRVAL_STATE_COOKING = "4"
ATTRVAL_STATE_PAUSED = "7"  # e.g. door opened during a cycle
ATTRVAL_STATE_COMPLETED = "13"  # shown for a few seconds at the end of a cycle
ATTRVAL_OPERATION_CANCEL = "1"  # same code as the HTTP oven cavity

CAVITY_STATE_MAP = {
    ATTRVAL_STATE_IDLE: MicrowaveCavityState.Idle,
    ATTRVAL_STATE_PROGRAMMING: MicrowaveCavityState.Idle,
    ATTRVAL_STATE_COOKING: MicrowaveCavityState.Cooking,
    ATTRVAL_STATE_PAUSED: MicrowaveCavityState.Paused,
    ATTRVAL_STATE_COMPLETED: MicrowaveCavityState.Completed,
}

COOK_TIMER_STATE_MAP = {
    "0": "idle",
    "1": "running",
    "2": "paused",
    "3": "completed",
}

TEMP_UNITS_MAP = {"0": "C", "1": "F"}


class Microwave(BaseMicrowave, Appliance):
    @override
    def get_cavity_state(self) -> MicrowaveCavityState | None:
        state_raw = self._get_attribute(ATTR_STATUS_STATE)
        if state_raw is None:
            return None
        state = CAVITY_STATE_MAP.get(state_raw)
        if state is None:
            LOGGER.debug(f"Unknown microwave state: {state_raw}")
        return state

    @override
    def get_door_status(self) -> MicrowaveDoorStatus | None:
        door_open = self.attr_value_to_bool(self._get_attribute(ATTR_DOOR_OPEN))
        if door_open is None:
            return None
        return MicrowaveDoorStatus.Open if door_open else MicrowaveDoorStatus.Closed

    @override
    def get_door_locked(self) -> bool | None:
        return None

    @override
    def get_cavity_light(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_LIGHT))

    @override
    async def set_cavity_light(self, on: bool) -> bool:
        return await self.send_attributes({ATTR_LIGHT: self.bool_to_attr_value(on)})

    @override
    def get_display_temperature(self) -> float | None:
        reported_temp = self._get_int_attribute(ATTR_DISPLAY_TEMP)
        if reported_temp is None or reported_temp == 0:
            return None
        # 1/10ths of a degree, like the HTTP ovens
        return reported_temp / 10

    @override
    def get_display_temperature_unit(self) -> str | None:
        return TEMP_UNITS_MAP.get(self._get_attribute(ATTR_TEMP_UNITS) or "")

    @override
    def get_turntable_enabled(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_TURNTABLE))

    @override
    def get_active_recipe_id(self) -> str | None:
        return None

    @override
    def get_recipe_execution_state(self) -> str | None:
        return None

    @override
    async def set_cook(
        self,
        recipe: Recipe,
        duration_seconds: int,
        power_level: int | None = None,
    ) -> bool:
        LOGGER.error("Starting a cook cycle is not supported on the HTTP API")
        return False

    @override
    async def stop_cook(self) -> bool:
        return await self.send_attributes(
            {ATTR_SET_OPERATIONS: ATTRVAL_OPERATION_CANCEL}
        )

    @override
    def get_mwo_power_level(self) -> int | None:
        # The HTTP API reports the power in watts, not as a percentage
        return None

    def get_cook_power_watts(self) -> int | None:
        return self._get_int_attribute(ATTR_COOK_POWER_WATTS)

    @override
    def get_cook_timer_state(self) -> str | None:
        state_raw = self._get_attribute(ATTR_COOK_TIME_STATE)
        if state_raw is None:
            return None
        state = COOK_TIMER_STATE_MAP.get(state_raw)
        if state is None:
            LOGGER.debug(f"Unknown microwave cook timer state: {state_raw}")
        return state

    @override
    def get_cook_timer_total_seconds(self) -> int | None:
        return self._get_int_attribute(ATTR_COOK_TIME_SET)

    @override
    def get_cook_timer_time_complete(self) -> int | None:
        return None

    def get_cook_time_remaining(self) -> int | None:
        return self._get_int_attribute(ATTR_COOK_TIME_REMAINING)

    def get_cook_time_elapsed(self) -> int | None:
        return self._get_int_attribute(ATTR_COOK_TIME_ELAPSED)

    def get_cycle_count(self) -> int | None:
        return self._get_int_attribute(ATTR_ODOMETER)

    def get_kitchen_timer(self, timer_id: int = 1) -> KitchenTimer:
        return KitchenTimer(appliance=self, timer_id=timer_id)

    @override
    def get_hood_light_level(self) -> HoodLightLevel | None:
        return None

    @override
    async def set_hood_light_level(self, level: HoodLightLevel) -> bool:
        LOGGER.error("Hood light is not supported on the HTTP API")
        return False

    @override
    def get_hood_light_color(self) -> HoodLightColor | None:
        return None

    @override
    async def set_hood_light_color(self, color: HoodLightColor) -> bool:
        LOGGER.error("Hood light color is not supported on the HTTP API")
        return False

    @override
    def get_hood_fan_speed(self) -> HoodFanSpeed | None:
        return None

    @override
    async def set_hood_fan_speed(self, speed: HoodFanSpeed) -> bool:
        LOGGER.error("Hood fan is not supported on the HTTP API")
        return False

    @override
    def get_remote_start_enabled(self) -> bool | None:
        return None

    @override
    def get_control_locked(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_CONTROL_LOCK))

    @override
    async def set_control_locked(self, on: bool) -> bool:
        return await self.send_attributes(
            {ATTR_CONTROL_LOCK: self.bool_to_attr_value(on)}
        )

    @override
    def get_quiet_mode(self) -> bool | None:
        return None

    @override
    async def set_quiet_mode(self, on: bool) -> bool:
        LOGGER.error("Quiet mode is not supported on the HTTP API")
        return False

    @override
    def get_sabbath_mode(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_SABBATH_MODE))

    @override
    async def set_sabbath_mode(self, on: bool) -> bool:
        return await self.send_attributes(
            {ATTR_SABBATH_MODE: self.bool_to_attr_value(on)}
        )

    @override
    def supports_hood_fan(self) -> bool:
        return False

    @override
    def supports_hood_light_level(self) -> bool:
        return False

    @override
    def supports_hood_light_color(self) -> bool:
        return False

    @override
    def supports_quiet_mode(self) -> bool:
        return False

    @override
    def supports_control_lock(self) -> bool:
        return True

    @override
    def supports_sabbath_mode(self) -> bool:
        return True
