import logging
from typing import override

from ..washer import MachineState
from ..washer import Washer as BaseWasher
from .appliance import Appliance

LOGGER = logging.getLogger(__name__)

ATTR_CYCLE_STATUS_SENSING = "WashCavity_CycleStatusSensing"
ATTR_CYCLE_STATUS_FILLING = "WashCavity_CycleStatusFilling"
ATTR_CYCLE_STATUS_SOAKING = "WashCavity_CycleStatusSoaking"
ATTR_CYCLE_STATUS_WASHING = "WashCavity_CycleStatusWashing"
ATTR_CYCLE_STATUS_RINSING = "WashCavity_CycleStatusRinsing"
ATTR_CYCLE_STATUS_SPINNING = "WashCavity_CycleStatusSpinning"
ATTR_CYCLE_STATUS_MACHINE_STATE = "Cavity_CycleStatusMachineState"
ATTR_CYCLE_STATUS_TIME_REMAINING = "Cavity_TimeStatusEstTimeRemaining"

ATTR_DISPENSE_1_LEVEL = "WashCavity_OpStatusBulkDispense1Level"
ATTR_DISPENSE_2_LEVEL = "WashCavity_OpStatusBulkDispense2Level"
ATTR_CYCLE_SELECT = "WashCavity_CycleSetCycleSelect"
ATTR_DOOR_OPEN = "Cavity_OpStatusDoorOpen"
ATTR_REMOTE_CONTROL_ENABLE = "XCat_RemoteSetRemoteControlEnable"

WASH_CYCLE_PAIR_SUPPORTED_MODEL = "WFW9620HBK3"
WASH_CYCLE_PAIRS: dict[int, tuple[str, str]] = {
    1: ("regular", "normal"),
    2: ("regular", "heavy_duty"),
    3: ("regular", "sanitize"),
    4: ("regular", "quick"),
    5: ("delicates", "normal"),
    10: ("whites", "normal"),
    11: ("towels", "normal"),
    16: ("regular", "wrinkle_control"),
    18: ("regular", "cold_wash"),
    22: ("bulky", "normal"),
    24: ("colors", "normal"),
    44: ("colors", "cold_wash"),
    46: ("colors", "heavy_duty"),
    47: ("colors", "quick"),
    48: ("colors", "sanitize"),
    49: ("colors", "wrinkle_control"),
    50: ("bulky", "cold_wash"),
    52: ("bulky", "heavy_duty"),
    53: ("bulky", "quick"),
    54: ("bulky", "wrinkle_control"),
    65: ("delicates", "cold_wash"),
    67: ("delicates", "heavy_duty"),
    68: ("delicates", "quick"),
    69: ("delicates", "sanitize"),
    70: ("delicates", "wrinkle_control"),
    82: ("towels", "cold_wash"),
    84: ("towels", "heavy_duty"),
    85: ("towels", "quick"),
    86: ("towels", "sanitize"),
    87: ("towels", "wrinkle_control"),
    88: ("whites", "cold_wash"),
    90: ("whites", "heavy_duty"),
    91: ("whites", "quick"),
    92: ("whites", "sanitize"),
    93: ("whites", "wrinkle_control"),
}
UTILITY_CYCLES = {8: "drain_spin", 20: "clean_washer"}

ATTRVAL_MACHINE_STATE_STANDBY = "0"
ATTRVAL_MACHINE_STATE_SETTING = "1"
ATTRVAL_MACHINE_STATE_DELAY_COUNT_DOWN_MODE = "2"
ATTRVAL_MACHINE_STATE_DELAY_PAUSE = "3"
ATTRVAL_MACHINE_STATE_SMART_DELAY = "4"
ATTRVAL_MACHINE_STATE_SMART_GRID_PAUSE = "5"
ATTRVAL_MACHINE_STATE_PAUSE = "6"
ATTRVAL_MACHINE_STATE_RUNNING_MAIN_CYCLE = "7"
ATTRVAL_MACHINE_STATE_RUNNING_POST_CYCLE = "8"
ATTRVAL_MACHINE_STATE_EXCEPTIONS = "9"
ATTRVAL_MACHINE_STATE_COMPLETE = "10"
ATTRVAL_MACHINE_STATE_POWER_FAILURE = "11"
ATTRVAL_MACHINE_STATE_SERVICE_DIAGNOSTIC = "12"
ATTRVAL_MACHINE_STATE_FACTORY_DIAGNOSTIC = "13"
ATTRVAL_MACHINE_STATE_LIFE_TEST = "14"
ATTRVAL_MACHINE_STATE_CUSTOMER_FOCUS_MODE = "15"
ATTRVAL_MACHINE_STATE_DEMO_MODE = "16"
ATTRVAL_MACHINE_STATE_HARD_STOP_OR_ERROR = "17"
ATTRVAL_MACHINE_STATE_SYSTEM_INIT = "18"

MACHINE_STATE_MAP = {
    ATTRVAL_MACHINE_STATE_STANDBY: MachineState.Standby,
    ATTRVAL_MACHINE_STATE_SETTING: MachineState.Setting,
    ATTRVAL_MACHINE_STATE_DELAY_COUNT_DOWN_MODE: MachineState.DelayCountdownMode,
    ATTRVAL_MACHINE_STATE_DELAY_PAUSE: MachineState.DelayPause,
    ATTRVAL_MACHINE_STATE_SMART_DELAY: MachineState.SmartDelay,
    ATTRVAL_MACHINE_STATE_SMART_GRID_PAUSE: MachineState.SmartGridPause,
    ATTRVAL_MACHINE_STATE_PAUSE: MachineState.Pause,
    ATTRVAL_MACHINE_STATE_RUNNING_MAIN_CYCLE: MachineState.RunningMainCycle,
    ATTRVAL_MACHINE_STATE_RUNNING_POST_CYCLE: MachineState.RunningPostCycle,
    ATTRVAL_MACHINE_STATE_EXCEPTIONS: MachineState.Exceptions,
    ATTRVAL_MACHINE_STATE_COMPLETE: MachineState.Complete,
    ATTRVAL_MACHINE_STATE_POWER_FAILURE: MachineState.PowerFailure,
    ATTRVAL_MACHINE_STATE_SERVICE_DIAGNOSTIC: MachineState.ServiceDiagnostic,
    ATTRVAL_MACHINE_STATE_FACTORY_DIAGNOSTIC: MachineState.FactoryDiagnostic,
    ATTRVAL_MACHINE_STATE_LIFE_TEST: MachineState.LifeTest,
    ATTRVAL_MACHINE_STATE_CUSTOMER_FOCUS_MODE: MachineState.CustomerFocusMode,
    ATTRVAL_MACHINE_STATE_DEMO_MODE: MachineState.DemoMode,
    ATTRVAL_MACHINE_STATE_HARD_STOP_OR_ERROR: MachineState.HardStopOrError,
    ATTRVAL_MACHINE_STATE_SYSTEM_INIT: MachineState.SystemInit,
}


class Washer(BaseWasher, Appliance):
    @override
    def get_machine_state(self) -> MachineState | None:
        state_raw = self._get_attribute(ATTR_CYCLE_STATUS_MACHINE_STATE)
        if state_raw is None:
            return None
        return MACHINE_STATE_MAP.get(state_raw, None)

    @override
    def get_cycle_status_sensing(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_CYCLE_STATUS_SENSING))

    @override
    def get_cycle_status_filling(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_CYCLE_STATUS_FILLING))

    @override
    def get_cycle_status_soaking(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_CYCLE_STATUS_SOAKING))

    @override
    def get_cycle_status_washing(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_CYCLE_STATUS_WASHING))

    @override
    def get_cycle_status_rinsing(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_CYCLE_STATUS_RINSING))

    @override
    def get_cycle_status_spinning(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_CYCLE_STATUS_SPINNING))

    @override
    def get_dispense_1_level(self) -> int | None:
        return self._get_int_attribute(ATTR_DISPENSE_1_LEVEL)

    @override
    def get_door_open(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_DOOR_OPEN))

    @override
    def get_time_remaining(self) -> int | None:
        return self._get_int_attribute(ATTR_CYCLE_STATUS_TIME_REMAINING)

    @override
    def get_remote_control_enabled(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_REMOTE_CONTROL_ENABLE))

    @override
    def get_dispense_2_level(self) -> int | None:
        return self._get_int_attribute(ATTR_DISPENSE_2_LEVEL)

    @override
    def get_wash_cycle_pair(self) -> tuple[str, str] | None:
        if self.appliance_info.model_number != WASH_CYCLE_PAIR_SUPPORTED_MODEL:
            return None
        cycle = self._get_int_attribute(ATTR_CYCLE_SELECT)
        return None if cycle is None else WASH_CYCLE_PAIRS.get(cycle)

    @override
    def get_utility_cycle(self) -> str | None:
        if self.appliance_info.model_number != WASH_CYCLE_PAIR_SUPPORTED_MODEL:
            return None
        cycle = self._get_int_attribute(ATTR_CYCLE_SELECT)
        return None if cycle is None else UTILITY_CYCLES.get(cycle)
