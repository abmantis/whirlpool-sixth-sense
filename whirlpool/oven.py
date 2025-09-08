import logging
from enum import Enum

from .appliance import Appliance

LOGGER = logging.getLogger(__name__)

ATTR_DISPLAY_BRIGHTNESS = "Sys_DisplaySetBrightnessPercent"
ATTR_CONTROL_LOCK = "Sys_OperationSetControlLock"
ATTR_SABBATH_MODE = "Sys_OperationSetSabbathModeEnabled"

ATTR_POSTFIX_DOOR_OPEN_STATUS = "OpStatusDoorOpen"
ATTR_POSTFIX_LIGHT_STATUS = "DisplaySetLightOn"
ATTR_POSTFIX_TARGET_TEMP = "CycleSetTargetTemp"
ATTR_POSTFIX_TEMP = "DisplStatusDisplayTemp"
ATTR_POSTFIX_COOK_TIME = "TimeStatusCycleTimeElapsed"
ATTR_POSTFIX_STATUS_STATE = "OpStatusState"
ATTR_POSTFIX_COOK_MODE = "CycleSetCommonMode"
ATTR_POSTFIX_MEAT_PROBE_STATUS = "AlertStatusMeatProbePluggedIn"
ATTR_POSTFIX_MEAT_PROBE_TARGET_TEMP = "CycleSetMeatProbeTargetTemp"
ATTR_POSTFIX_SET_OPERATION = "OpSetOperations"

ATTRVAL_CAVITY_STATE_STANDBY = "0"
ATTRVAL_CAVITY_STATE_PREHEATING = "1"
ATTRVAL_CAVITY_STATE_COOKING = "2"
ATTRVAL_CAVITY_STATE_NOT_PRESENT = "4"

ATTRVAL_CAVITY_OPERATION_CANCEL = "1"
ATTRVAL_CAVITY_OPERATION_START = "2"
ATTRVAL_CAVITY_OPERATION_MODIFY = "4"
ATTRVAL_CAVITY_OPERATION_PAUSE = "5"

ATTRVAL_COOK_MODE_STANDBY = "0"
ATTRVAL_COOK_MODE_BAKE = "2"
ATTRVAL_COOK_MODE_CONVECT_BAKE = "6"
ATTRVAL_COOK_MODE_BROIL = "8"
ATTRVAL_COOK_MODE_CONVECT_BROIL = "9"
ATTRVAL_COOK_MODE_CONVECT_ROAST = "16"
ATTRVAL_COOK_MODE_KEEP_WARM = "24"
ATTRVAL_COOK_MODE_AIR_FRY = "41"

ATTR_POSTFIX_KITCHEN_TIMER_TIME_REMAINING = "StatusTimeRemaining"
ATTR_POSTFIX_KITCHEN_TIMER_STATUS = "StatusState"
ATTR_POSTFIX_KITCHEN_TIMER_SET_TIME = "SetTimeSet"
ATTR_POSTFIX_KITCHEN_TIMER_SET_OPS = "SetOperations"

ATTRVAL_KITCHEN_TIMER_STATE_STANDBY = "0"
ATTRVAL_KITCHEN_TIMER_STATE_RUNNING = "1"
ATTRVAL_KITCHEN_TIMER_STATE_COMPLETED = "3"

ATTRVAL_KITCHEN_TIMER_OPERATION_CANCEL = "1"
ATTRVAL_KITCHEN_TIMER_OPERATION_START = "2"


class Cavity(Enum):
    Upper = 0
    Lower = 1


CAVITY_PREFIX_MAP = {Cavity.Upper: "OvenUpperCavity", Cavity.Lower: "OvenLowerCavity"}


# todo: figure out/plug in the other enums
class CookMode(Enum):
    Standby = 0
    Bake = 2
    ConvectBake = 6
    Broil = 8
    ConvectBroil = 9
    ConvectRoast = 16
    KeepWarm = 24
    AirFry = 41


COOK_MODE_MAP = {
    CookMode.Standby: ATTRVAL_COOK_MODE_STANDBY,
    CookMode.Bake: ATTRVAL_COOK_MODE_BAKE,
    CookMode.ConvectBake: ATTRVAL_COOK_MODE_CONVECT_BAKE,
    CookMode.Broil: ATTRVAL_COOK_MODE_BROIL,
    CookMode.ConvectBroil: ATTRVAL_COOK_MODE_CONVECT_BROIL,
    CookMode.ConvectRoast: ATTRVAL_COOK_MODE_CONVECT_ROAST,
    CookMode.KeepWarm: ATTRVAL_COOK_MODE_KEEP_WARM,
    CookMode.AirFry: ATTRVAL_COOK_MODE_AIR_FRY,
}


# todo: figure out/plug in the other enums
class CookOperation(Enum):
    Cancel = 1
    Start = 2
    Modify = 4
    Pause = 5


COOK_OPERATION_MAP = {
    CookOperation.Cancel: ATTRVAL_CAVITY_OPERATION_CANCEL,
    CookOperation.Start: ATTRVAL_CAVITY_OPERATION_START,
    CookOperation.Modify: ATTRVAL_CAVITY_OPERATION_MODIFY,
    CookOperation.Pause: ATTRVAL_CAVITY_OPERATION_PAUSE,
}


# todo: figure out/plug in the other enums
class CavityState(Enum):
    Standby = 0
    Preheating = 1
    Cooking = 2
    NotPresent = 4


CAVITY_STATE_MAP = {
    CavityState.Standby: ATTRVAL_CAVITY_STATE_STANDBY,
    CavityState.Preheating: ATTRVAL_CAVITY_STATE_PREHEATING,
    CavityState.Cooking: ATTRVAL_CAVITY_STATE_COOKING,
    CavityState.NotPresent: ATTRVAL_CAVITY_STATE_NOT_PRESENT,
}


# todo: figure out/plug in what state = 2 is
class KitchenTimerState(Enum):
    Standby = 0
    Running = 1
    Completed = 3


KITCHEN_TIMER_STATE_MAP = {
    KitchenTimerState.Standby: ATTRVAL_KITCHEN_TIMER_STATE_STANDBY,
    KitchenTimerState.Running: ATTRVAL_KITCHEN_TIMER_STATE_RUNNING,
    KitchenTimerState.Completed: ATTRVAL_KITCHEN_TIMER_STATE_COMPLETED,
}


class KitchenTimerOperations(Enum):
    Cancel = 1
    Start = 2


KITCHEN_TIMER_OPERATIONS_MAP = {
    KitchenTimerOperations.Cancel: ATTRVAL_KITCHEN_TIMER_OPERATION_CANCEL,
    KitchenTimerOperations.Start: ATTRVAL_KITCHEN_TIMER_OPERATION_START,
}


class KitchenTimer:
    def __init__(self, appliance: Appliance, timer_id: int = 1):
        self._timer_id = timer_id
        self._appliance = appliance
        self._attr_prefix = f"KitchenTimer{timer_id:02d}_"

    def get_total_time(self):
        return self._appliance._get_attribute(
            self._attr_prefix + ATTR_POSTFIX_KITCHEN_TIMER_SET_TIME
        )

    def get_remaining_time(self):
        return self._appliance._get_attribute(
            self._attr_prefix + ATTR_POSTFIX_KITCHEN_TIMER_TIME_REMAINING
        )

    def get_state(self):
        state_raw = self._appliance._get_attribute(
            self._attr_prefix + ATTR_POSTFIX_KITCHEN_TIMER_STATUS
        )
        for k, v in KITCHEN_TIMER_STATE_MAP.items():
            if v == state_raw:
                return k
        LOGGER.error("Unknown kitchen timer state: " + str(state_raw))
        return None

    async def set_timer(
        self,
        timer_time: int,
        operation: KitchenTimerOperations = KitchenTimerOperations.Start,
    ) -> bool:
        return await self._appliance.send_attributes(
            {
                self._attr_prefix + ATTR_POSTFIX_KITCHEN_TIMER_SET_TIME: str(
                    timer_time
                ),
                self._attr_prefix
                + ATTR_POSTFIX_KITCHEN_TIMER_SET_OPS: KITCHEN_TIMER_OPERATIONS_MAP[
                    operation
                ],
            }
        )

    async def cancel_timer(self) -> bool:
        return await self._appliance.send_attributes(
            {
                self._attr_prefix
                + ATTR_POSTFIX_KITCHEN_TIMER_SET_OPS: KITCHEN_TIMER_OPERATIONS_MAP[
                    KitchenTimerOperations.Cancel
                ]
            }
        )


class Oven(Appliance):
    def get_meat_probe_status(self, cavity: Cavity = Cavity.Upper):
        return self.attr_value_to_bool(
            self._get_attribute(
                CAVITY_PREFIX_MAP[cavity] + "_" + ATTR_POSTFIX_MEAT_PROBE_STATUS
            )
        )

    def get_door_opened(self, cavity: Cavity = Cavity.Upper):
        return self.attr_value_to_bool(
            self._get_attribute(
                CAVITY_PREFIX_MAP[cavity] + "_" + ATTR_POSTFIX_DOOR_OPEN_STATUS
            )
        )

    def get_display_brightness_percent(self) -> int | None:
        brightness = self._get_attribute(ATTR_DISPLAY_BRIGHTNESS)
        return int(brightness) if brightness is not None else None

    async def set_display_brightness_percent(self, pct: int) -> bool:
        return await self.send_attributes({ATTR_DISPLAY_BRIGHTNESS: str(pct)})

    def get_cook_time(self, cavity: Cavity = Cavity.Upper):
        time = self._get_attribute(
            CAVITY_PREFIX_MAP[cavity] + "_" + ATTR_POSTFIX_COOK_TIME
        )
        return int(time) if time is not None else None

    def get_control_locked(self):
        return self.attr_value_to_bool(self._get_attribute(ATTR_CONTROL_LOCK))

    async def set_control_locked(self, on: bool) -> bool:
        return await self.send_attributes(
            {ATTR_CONTROL_LOCK: self.bool_to_attr_value(on)}
        )

    def get_light(self, cavity: Cavity = Cavity.Upper):
        return self.attr_value_to_bool(
            self._get_attribute(
                CAVITY_PREFIX_MAP[cavity] + "_" + ATTR_POSTFIX_LIGHT_STATUS
            )
        )

    async def set_light(self, on: bool, cavity: Cavity = Cavity.Upper) -> bool:
        return await self.send_attributes(
            {
                CAVITY_PREFIX_MAP[cavity]
                + "_"
                + ATTR_POSTFIX_LIGHT_STATUS: self.bool_to_attr_value(on)
            }
        )

    def get_temp(self, cavity: Cavity = Cavity.Upper):
        reported_temp = self._get_attribute(
            CAVITY_PREFIX_MAP[cavity] + "_" + ATTR_POSTFIX_TEMP
        )
        # temperatures are returned in 1/10ths of a degree Celsius,
        # e.g. 2600 returned = 260C
        return None if reported_temp is None else int(reported_temp) / 10

    def get_target_temp(self, cavity: Cavity = Cavity.Upper):
        reported_temp = self._get_attribute(
            CAVITY_PREFIX_MAP[cavity] + "_" + ATTR_POSTFIX_TARGET_TEMP
        )
        # temperatures are returned in 1/10ths of a degree Celsius,
        # e.g. 2600 returned = 260C
        return None if reported_temp is None else int(reported_temp) / 10

    def get_cavity_state(self, cavity: Cavity = Cavity.Upper):
        state_raw = self._get_attribute(
            CAVITY_PREFIX_MAP[cavity] + "_" + ATTR_POSTFIX_STATUS_STATE
        )
        for k, v in CAVITY_STATE_MAP.items():
            if v == state_raw:
                return k
        LOGGER.error("Unknown cavity state: " + str(state_raw))
        return None

    def get_oven_cavity_exists(self, cavity: Cavity):
        cavity_state = self.get_cavity_state(cavity=cavity)
        return cavity_state is not None and cavity_state != CavityState.NotPresent

    # todo: persist the kitchen timer objects in the object
    def get_kitchen_timer(self, timer_id=1):
        timer = KitchenTimer(appliance=self, timer_id=timer_id)
        return timer

    def get_cook_mode(self, cavity: Cavity = Cavity.Upper):
        cook_mode_raw = self._get_attribute(
            CAVITY_PREFIX_MAP[cavity] + "_" + ATTR_POSTFIX_COOK_MODE
        )
        for k, v in COOK_MODE_MAP.items():
            if v == cook_mode_raw:
                return k
        LOGGER.error("Unknown cook mode: " + str(cook_mode_raw))
        return None

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
        cavity_prefix = CAVITY_PREFIX_MAP[cavity] + "_"
        attrs: dict[str, str] = {
            cavity_prefix + ATTR_POSTFIX_COOK_MODE: COOK_MODE_MAP[mode],
            cavity_prefix + ATTR_POSTFIX_TARGET_TEMP: str(round(target_temp * 10)),
            cavity_prefix + ATTR_POSTFIX_SET_OPERATION: COOK_OPERATION_MAP[
                operation_type
            ],
        }
        if meat_probe_target_temp is not None:
            attrs[cavity_prefix + ATTR_POSTFIX_MEAT_PROBE_TARGET_TEMP] = str(
                round(meat_probe_target_temp * 10)
            )

        return await self.send_attributes(attrs)

    async def stop_cook(self, cavity: Cavity = Cavity.Upper) -> bool:
        return await self.send_attributes(
            {
                CAVITY_PREFIX_MAP[cavity]
                + "_"
                + ATTR_POSTFIX_SET_OPERATION: COOK_OPERATION_MAP[CookOperation.Cancel]
            }
        )

    def get_sabbath_mode(self):
        return self.attr_value_to_bool(self._get_attribute(ATTR_SABBATH_MODE))

    async def set_sabbath_mode(self, on: bool) -> bool:
        return await self.send_attributes(
            {ATTR_SABBATH_MODE: self.bool_to_attr_value(on)}
        )
