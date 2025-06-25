from enum import Enum

from .appliance import Appliance

ATTR_CYCLE_STATUS_SENSING = "WashCavity_CycleStatusSensing"
ATTR_CYCLE_STATUS_FILLING = "WashCavity_CycleStatusFilling"
ATTR_CYCLE_STATUS_SOAKING = "WashCavity_CycleStatusSoaking"
ATTR_CYCLE_STATUS_WASHING = "WashCavity_CycleStatusWashing"
ATTR_CYCLE_STATUS_RINSING = "WashCavity_CycleStatusRinsing"
ATTR_CYCLE_STATUS_SPINNING = "WashCavity_CycleStatusSpinning"
ATTR_CYCLE_STATUS_MACHINE_STATE = "Cavity_CycleStatusMachineState"
ATTR_CYCLE_STATUS_TIME_REMAINING = "Cavity_TimeStatusEstTimeRemaining"

ATTR_DISPENSE_1_LEVEL = "WashCavity_OpStatusBulkDispense1Level"
ATTR_DOOR_OPEN = "Cavity_OpStatusDoorOpen"

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


class MachineState(Enum):
    Standby = 0
    Setting = 1
    DelayCountdownMode = 2
    DelayPause = 3
    SmartDelay = 4
    SmartGridPause = 5
    Pause = 6
    RunningMainCycle = 7
    RunningPostCycle = 8
    Exceptions = 9
    Complete = 10
    PowerFailure = 11
    ServiceDiagnostic = 12
    FactoryDiagnostic = 13
    LifeTest = 14
    CustomerFocusMode = 15
    DemoMode = 16
    HardStopOrError = 17
    SystemInit = 18


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
    ATTRVAL_MACHINE_STATE_SYSTEM_INIT: MachineState.SystemInit
}


class Washer(Appliance):
    def get_machine_state(self) -> MachineState | None:
        state_raw = self._get_attribute(ATTR_CYCLE_STATUS_MACHINE_STATE)
        if state_raw is None:
            return None
        return MACHINE_STATE_MAP.get(state_raw, None)

    def get_cycle_status_sensing(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_CYCLE_STATUS_SENSING))

    def get_cycle_status_filling(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_CYCLE_STATUS_FILLING))

    def get_cycle_status_soaking(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_CYCLE_STATUS_SOAKING))

    def get_cycle_status_washing(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_CYCLE_STATUS_WASHING))

    def get_cycle_status_rinsing(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_CYCLE_STATUS_RINSING))

    def get_cycle_status_spinning(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_CYCLE_STATUS_SPINNING))

    def get_dispense_1_level(self) -> int | None:
        return self._get_int_attribute(ATTR_DISPENSE_1_LEVEL)

    def get_door_open(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_DOOR_OPEN))

    def get_time_remaining(self) -> int | None:
        return self._get_int_attribute(ATTR_CYCLE_STATUS_TIME_REMAINING)
