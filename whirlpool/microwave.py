import logging
from enum import Enum

from whirlpool.appliance import Appliance

LOGGER = logging.getLogger(__name__)

# Common attributes
ATTR_DISPLAY_BRIGHTNESS = "Sys_DisplaySetBrightnessPercent"
ATTR_CONTROL_LOCK = "Sys_OperationSetControlLock"
ATTR_SABBATH_MODE = "Sys_OperationSetSabbathModeEnabled"

# Microwave specific attributes (Mwo_ prefix)
ATTR_MWO_PREFIX = "Mwo_"

ATTR_MWO_DOOR_OPEN = "Mwo_OperationStatusDoorOpen"
ATTR_MWO_STATE = "Mwo_OperationStatusState"
ATTR_MWO_LIGHT = "Mwo_DisplaySetLightOn"
ATTR_MWO_DISPLAY_TEMP = "Mwo_DisplayStatusDisplayTemp"
ATTR_MWO_TARGET_TEMP = "Mwo_CycleSetTargetTemp"
ATTR_MWO_COOK_TIME_SET = "Mwo_TimeSetCookTimeSet"
ATTR_MWO_COOK_TIME_REMAINING = "Mwo_TimeStatusCookTimeRemaining"
ATTR_MWO_COOK_TIME_ELAPSED = "Mwo_TimeStatusCycleTimeElapsed"
ATTR_MWO_COOK_POWER = "Mwo_CycleSetCookPower"
ATTR_MWO_COOK_POWER_WATTS = "Mwo_CycleSetCookPowerWatts"
ATTR_MWO_OPERATIONS = "Mwo_OperationSetOperations"
ATTR_MWO_IDLE = "Mwo_ModeStatusIdle"
ATTR_MWO_ODOMETER = "Mwo_CycleStatusOdometer"
ATTR_MWO_MEAT_PROBE_PLUGGED = "Mwo_OperationStatusMeatProbePluggedIn"
ATTR_MWO_MEAT_PROBE_TEMP = "Mwo_OperationStatusMeatProbeRawTemp"
ATTR_MWO_MEAT_PROBE_TARGET = "Mwo_CycleSetMeatProbeTargetTemp"
ATTR_MWO_DELAY_TIME_REMAINING = "Mwo_TimeStatusDelayTimeRemaining"
ATTR_MWO_TURNTABLE = "Mwo_CycleSetTurntable"
ATTR_MWO_PREHEAT = "Mwo_CycleSetPreheatOn"
ATTR_MWO_BROWNING = "Mwo_CycleSetBrowning"
ATTR_MWO_BROIL_LEVEL = "Mwo_CycleSetBroilLevel"
ATTR_MWO_DONENESS = "Mwo_CycleSetDoneness"

# Cook modes
ATTR_MWO_MODE_COOK = "Mwo_ModeSetCook"
ATTR_MWO_MODE_REHEAT = "Mwo_ModeSetReheat"
ATTR_MWO_MODE_DEFROST = "Mwo_ModeSetDefrost"
ATTR_MWO_MODE_POPCORN = "Mwo_ModeSetPopcorn"
ATTR_MWO_MODE_KEEP_WARM = "Mwo_ModeSetKeepWarm"
ATTR_MWO_MODE_STEAM_COOK = "Mwo_ModeSetSteamCook"
ATTR_MWO_MODE_CONVECT_BAKE = "Mwo_ModeSetConvectBake"
ATTR_MWO_MODE_CONVECT_ROAST = "Mwo_ModeSetConvectRoast"
ATTR_MWO_MODE_BROIL_GRILL = "Mwo_ModeSetBroilAndGrill"
ATTR_MWO_MODE_REGULAR_BAKE = "Mwo_ModeSetRegularBake"

# Kitchen timer
ATTR_KITCHEN_TIMER_TIME_REMAINING = "KitchenTimer01_StatusTimeRemaining"
ATTR_KITCHEN_TIMER_STATE = "KitchenTimer01_StatusState"
ATTR_KITCHEN_TIMER_SET_TIME = "KitchenTimer01_SetTimeSet"
ATTR_KITCHEN_TIMER_SET_OPS = "KitchenTimer01_SetOperations"

# State values
ATTRVAL_STATE_STANDBY = "0"
ATTRVAL_STATE_RUNNING = "1"
ATTRVAL_STATE_PAUSED = "2"
ATTRVAL_STATE_COMPLETE = "3"

# Operation values
ATTRVAL_OPERATION_CANCEL = "1"
ATTRVAL_OPERATION_START = "2"
ATTRVAL_OPERATION_PAUSE = "5"


class MicrowaveState(Enum):
    Standby = 0
    Running = 1
    Paused = 2
    Complete = 3


MICROWAVE_STATE_MAP = {
    MicrowaveState.Standby: ATTRVAL_STATE_STANDBY,
    MicrowaveState.Running: ATTRVAL_STATE_RUNNING,
    MicrowaveState.Paused: ATTRVAL_STATE_PAUSED,
    MicrowaveState.Complete: ATTRVAL_STATE_COMPLETE,
}


class MicrowaveOperation(Enum):
    Cancel = 1
    Start = 2
    Pause = 5


MICROWAVE_OPERATION_MAP = {
    MicrowaveOperation.Cancel: ATTRVAL_OPERATION_CANCEL,
    MicrowaveOperation.Start: ATTRVAL_OPERATION_START,
    MicrowaveOperation.Pause: ATTRVAL_OPERATION_PAUSE,
}


class KitchenTimerState(Enum):
    Standby = 0
    Running = 1
    Completed = 3


class Microwave(Appliance):
    """Microwave appliance class."""

    def get_door_opened(self) -> bool | None:
        """Return True if door is open."""
        return self.attr_value_to_bool(self._get_attribute(ATTR_MWO_DOOR_OPEN))

    def get_state(self) -> MicrowaveState | None:
        """Return current microwave state."""
        state_raw = self._get_attribute(ATTR_MWO_STATE)
        for k, v in MICROWAVE_STATE_MAP.items():
            if v == state_raw:
                return k
        LOGGER.error("Unknown microwave state: %s", state_raw)
        return None

    def get_is_idle(self) -> bool | None:
        """Return True if microwave is idle."""
        return self.attr_value_to_bool(self._get_attribute(ATTR_MWO_IDLE))

    def get_light(self) -> bool | None:
        """Return True if light is on."""
        return self.attr_value_to_bool(self._get_attribute(ATTR_MWO_LIGHT))

    async def set_light(self, on: bool) -> bool:
        """Turn light on/off."""
        return await self.send_attributes(
            {ATTR_MWO_LIGHT: self.bool_to_attr_value(on)}
        )

    def get_display_brightness_percent(self) -> int | None:
        """Return display brightness percentage."""
        brightness = self._get_attribute(ATTR_DISPLAY_BRIGHTNESS)
        return int(brightness) if brightness is not None else None

    async def set_display_brightness_percent(self, pct: int) -> bool:
        """Set display brightness percentage."""
        return await self.send_attributes({ATTR_DISPLAY_BRIGHTNESS: str(pct)})

    def get_temp(self) -> float | None:
        """Return current display temperature in Celsius."""
        reported_temp = self._get_int_attribute(ATTR_MWO_DISPLAY_TEMP)
        if reported_temp is None or reported_temp == 0:
            return None
        return reported_temp / 10

    def get_target_temp(self) -> float | None:
        """Return target temperature in Celsius."""
        reported_temp = self._get_int_attribute(ATTR_MWO_TARGET_TEMP)
        if reported_temp is None or reported_temp == 0:
            return None
        return reported_temp / 10

    def get_cook_time_remaining(self) -> int | None:
        """Return remaining cook time in seconds."""
        time = self._get_attribute(ATTR_MWO_COOK_TIME_REMAINING)
        return int(time) if time is not None else None

    def get_cook_time_elapsed(self) -> int | None:
        """Return elapsed cook time in seconds."""
        time = self._get_attribute(ATTR_MWO_COOK_TIME_ELAPSED)
        return int(time) if time is not None else None

    def get_cook_power(self) -> int | None:
        """Return cook power level."""
        power = self._get_attribute(ATTR_MWO_COOK_POWER)
        return int(power) if power is not None else None

    def get_cook_power_watts(self) -> int | None:
        """Return cook power in watts."""
        power = self._get_attribute(ATTR_MWO_COOK_POWER_WATTS)
        return int(power) if power is not None else None

    def get_control_locked(self) -> bool | None:
        """Return True if controls are locked."""
        return self.attr_value_to_bool(self._get_attribute(ATTR_CONTROL_LOCK))

    async def set_control_locked(self, on: bool) -> bool:
        """Lock/unlock controls."""
        return await self.send_attributes(
            {ATTR_CONTROL_LOCK: self.bool_to_attr_value(on)}
        )

    def get_turntable(self) -> bool | None:
        """Return True if turntable is enabled."""
        return self.attr_value_to_bool(self._get_attribute(ATTR_MWO_TURNTABLE))

    def get_meat_probe_status(self) -> bool | None:
        """Return True if meat probe is plugged in."""
        return self.attr_value_to_bool(self._get_attribute(ATTR_MWO_MEAT_PROBE_PLUGGED))

    def get_meat_probe_temp(self) -> float | None:
        """Return meat probe temperature."""
        temp = self._get_int_attribute(ATTR_MWO_MEAT_PROBE_TEMP)
        if temp is None or temp == 0:
            return None
        return temp / 10

    def get_cycle_count(self) -> int | None:
        """Return total cycle count (odometer)."""
        count = self._get_attribute(ATTR_MWO_ODOMETER)
        return int(count) if count is not None else None

    def get_sabbath_mode(self) -> bool | None:
        """Return True if sabbath mode is enabled."""
        return self.attr_value_to_bool(self._get_attribute(ATTR_SABBATH_MODE))

    async def set_sabbath_mode(self, on: bool) -> bool:
        """Enable/disable sabbath mode."""
        return await self.send_attributes(
            {ATTR_SABBATH_MODE: self.bool_to_attr_value(on)}
        )

    def get_kitchen_timer_remaining(self) -> int | None:
        """Return kitchen timer remaining time in seconds."""
        time = self._get_attribute(ATTR_KITCHEN_TIMER_TIME_REMAINING)
        return int(time) if time is not None else None

    def get_kitchen_timer_state(self) -> KitchenTimerState | None:
        """Return kitchen timer state."""
        state_raw = self._get_attribute(ATTR_KITCHEN_TIMER_STATE)
        if state_raw == "0":
            return KitchenTimerState.Standby
        elif state_raw == "1":
            return KitchenTimerState.Running
        elif state_raw == "3":
            return KitchenTimerState.Completed
        return None

    async def cancel_cook(self) -> bool:
        """Cancel current cook operation."""
        return await self.send_attributes(
            {ATTR_MWO_OPERATIONS: ATTRVAL_OPERATION_CANCEL}
        )
