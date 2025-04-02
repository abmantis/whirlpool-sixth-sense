import logging
from enum import Enum

from .appliance import Appliance

LOGGER = logging.getLogger(__name__)

ATTR_CYCLE_STATUS_SENSING = "WashCavity_CycleStatusSensing"
ATTR_CYCLE_STATUS_FILLING = "WashCavity_CycleStatusFilling"
ATTR_CYCLE_STATUS_SOAKING = "WashCavity_CycleStatusSoaking"
ATTR_CYCLE_STATUS_WASHING = "WashCavity_CycleStatusWashing"
ATTR_CYCLE_STATUS_RINSING = "WashCavity_CycleStatusRinsing"
ATTR_CYCLE_STATUS_SPINNING = "WashCavity_CycleStatusSpinning"
ATTR_DISPENSE_1_LEVEL = "WashCavity_OpStatusBulkDispense1Level"
ATTR_DOOR_OPEN = "Cavity_OpStatusDoorOpen"
ATTR_MACHINE_STATE = "Cavity_CycleStatusMachineState"
ATTR_TIME_REMAINING = "Cavity_TimeStatusEstTimeRemaining"

ATTRVAL_MACHINE_STATE_STANDBY = "0"
ATTRVAL_MACHINE_STATE_SETTING = "1"
ATTRVAL_MACHINE_STATE_DELAYCOUNTDOWNMODE = "2"
ATTRVAL_MACHINE_STATE_DELAYPAUSE = "3"
ATTRVAL_MACHINE_STATE_SMARTDELAY = "4"
ATTRVAL_MACHINE_STATE_SMARTGRIDPAUSE = "5"
ATTRVAL_MACHINE_STATE_PAUSE = "6"
ATTRVAL_MACHINE_STATE_RUNNINGMAINCYCLE = "7"
ATTRVAL_MACHINE_STATE_RUNNINGPOSTCYCLE = "8"
ATTRVAL_MACHINE_STATE_EXCEPTIONS = "9"
ATTRVAL_MACHINE_STATE_COMPLETE = "10"
ATTRVAL_MACHINE_STATE_POWERFAILURE = "11"
ATTRVAL_MACHINE_STATE_SERVICEDIAGNOSTIC = "12"
ATTRVAL_MACHINE_STATE_FACTORYDIAGNOSTIC = "13"
ATTRVAL_MACHINE_STATE_LIFETEST = "14"
ATTRVAL_MACHINE_STATE_CUSTOMERFOCUSMODE = "15"
ATTRVAL_MACHINE_STATE_DEMOMODE = "16"
ATTRVAL_MACHINE_STATE_HARDSTOPORERROR = "17"
ATTRVAL_MACHINE_STATE_SYSTEMINIT = "18"


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
    MachineState.Standby: ATTRVAL_MACHINE_STATE_STANDBY,
    MachineState.Setting: ATTRVAL_MACHINE_STATE_SETTING,
    MachineState.DelayCountdownMode: ATTRVAL_MACHINE_STATE_DELAYCOUNTDOWNMODE,
    MachineState.DelayPause: ATTRVAL_MACHINE_STATE_DELAYPAUSE,
    MachineState.SmartDelay: ATTRVAL_MACHINE_STATE_SMARTDELAY,
    MachineState.SmartGridPause: ATTRVAL_MACHINE_STATE_SMARTGRIDPAUSE,
    MachineState.Pause: ATTRVAL_MACHINE_STATE_PAUSE,
    MachineState.RunningMainCycle: ATTRVAL_MACHINE_STATE_RUNNINGMAINCYCLE,
    MachineState.RunningPostCycle: ATTRVAL_MACHINE_STATE_RUNNINGPOSTCYCLE,
    MachineState.Exceptions: ATTRVAL_MACHINE_STATE_EXCEPTIONS,
    MachineState.Complete: ATTRVAL_MACHINE_STATE_COMPLETE,
    MachineState.PowerFailure: ATTRVAL_MACHINE_STATE_POWERFAILURE,
    MachineState.ServiceDiagnostic: ATTRVAL_MACHINE_STATE_SERVICEDIAGNOSTIC,
    MachineState.FactoryDiagnostic: ATTRVAL_MACHINE_STATE_FACTORYDIAGNOSTIC,
    MachineState.LifeTest: ATTRVAL_MACHINE_STATE_LIFETEST,
    MachineState.CustomerFocusMode: ATTRVAL_MACHINE_STATE_CUSTOMERFOCUSMODE,
    MachineState.DemoMode: ATTRVAL_MACHINE_STATE_DEMOMODE,
    MachineState.HardStopOrError: ATTRVAL_MACHINE_STATE_HARDSTOPORERROR,
    MachineState.SystemInit: ATTRVAL_MACHINE_STATE_SYSTEMINIT,
}


class WasherDryer(Appliance):
    def get_machine_state(self) -> MachineState | None:
        state_raw = self._get_attribute(ATTR_MACHINE_STATE)
        for k, v in MACHINE_STATE_MAP.items():
            if v == state_raw:
                return k
        return None

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
        return self._get_int_attribute(ATTR_TIME_REMAINING)
