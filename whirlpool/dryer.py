import logging
from enum import Enum

from .appliance import Appliance
from .types import ApplianceData, ApplianceKind

LOGGER = logging.getLogger(__name__)

# Machine State
ATTR_MACHINE_STATE = "Cavity_CycleStatusMachineState"

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
ATTRVAL_MACHINE_STATE_MYSTERY = "19" # Observed on "Maytag MGD6230HW3"

# Cavity
ATTR_OP_STATUS_DOOROPEN = "Cavity_OpStatusDoorOpen"
ATTR_TIME_STATUS_ESTTIMEREMAINING = "Cavity_TimeStatusEstTimeRemaining"
ATTR_DISPLAY_SET_DRUMLIGHTON = "Cavity_DisplaySetDrumLightOn"

# DryCavity
ATTR_CHANGE_STATUS_EXTRAPOWERCHANGEABLE = "Cavity_ChangeStatusExtraPowerChangeable"
ATTR_CHANGE_STATUS_STEAMCHANGEABLE = "Cavity_ChangeStatusSteamChangeable"
ATTR_CHANGE_STATUS_CYCLESELECT = "DryCavity_ChangeStatusCycleSelect"
ATTR_CHANGE_STATUS_DRYNESS = "DryCavity_ChangeStatusDryness"
ATTR_CHANGE_STATUS_MANUALDRYTIME = "DryCavity_ChangeStatusManualDryTime"
ATTR_CHANGE_STATUS_STATICGUARD = "DryCavity_ChangeStatusStaticGuard"
ATTR_CHANGE_STATUS_TEMPERATURE = "DryCavity_ChangeStatusTemperature"
ATTR_CHANGE_STATUS_WRINKLESHIELD = "DryCavity_ChangeStatusWrinkleShield"

ATTR_CYCLE_SET_CYCLESELECT = "DryCavity_CycleSetCycleSelect"

ATTRVAL_CYCLESET_REGULAR = 1
ATTRVAL_CYCLESET_HEAVY_DUTY = 2
ATTRVAL_CYCLESET_WHITES = 16
ATTRVAL_CYCLESET_TOWELS = 15
ATTRVAL_CYCLESET_BULKY_ITEMS = 6
ATTRVAL_CYCLESET_QUICK_DRY = 7    
ATTRVAL_CYCLESET_DELICATES = 4
ATTRVAL_CYCLESET_WRINKLE_CONTROL = 5
ATTRVAL_CYCLESET_NORMAL = 41
ATTRVAL_CYCLESET_TIMED_DRY = 11

ATTR_CYCLE_SET_DRYNESS = "DryCavity_CycleSetDryness"

ATTRVAL_DRYNESS_LOW = 1
ATTRVAL_DRYNESS_NORMAL = 4
ATTRVAL_DRYNESS_HIGH = 7

ATTR_CYCLE_SET_MANUALDRYTIME = "DryCavity_CycleSetManualDryTime"
ATTR_CYCLE_SET_WRINKLESHIELD = "DryCavity_CycleSetWrinkleShield"

ATTR_CYCLE_SET_TEMPERATURE = "DryCavity_CycleSetTemperature"

ATTRVAL_TEMPERATURE_LOW = 2
ATTRVAL_TEMPERATURE_MEDIUM = 5
ATTRVAL_TEMPERATURE_MEDIUM_HIGH = 6
ATTRVAL_TEMPERATURE_HIGH = 8


ATTR_CYCLE_STATUS_AIRFLOWSTATUS = "DryCavity_CycleStatusAirFlowStatus"
ATTR_CYCLE_STATUS_COOLDOWN = "DryCavity_CycleStatusCoolDown"
ATTR_CYCLE_STATUS_DAMP = "DryCavity_CycleStatusDamp"
ATTR_CYCLE_STATUS_DRYING = "DryCavity_CycleStatusDrying"
ATTR_CYCLE_STATUS_LIMITEDCYCLE = "DryCavity_CycleStatusLimitedCycle"
ATTR_CYCLE_STATUS_SENSING = "DryCavity_CycleStatusSensing"
ATTR_CYCLE_STATUS_STATICREDUCE = "DryCavity_CycleStatusStaticReduce"
ATTR_CYCLE_STATUS_STEAMING = "DryCavity_CycleStatusSteaming"
ATTR_CYCLE_STATUS_WET = "DryCavity_CycleStatusWet"

# DrySys
ATTR_OP_SET_DAMPNOTIFICATIONTONEVOLUME = "DrySys_OpSetDampNotificationToneVolume" 

# Sys
ATTR_OP_SET_ALERTTONEVOLUME = "Sys_OpSetAlertToneVolume"

# XCat
ATTR_ODOMETER_STATUS_CYCLECOUNT = "XCat_OdometerStatusCycleCount"
ATTR_ODOMETER_STATUS_RUNNINGHOURS = "XCat_OdometerStatusRunningHours"
ATTR_ODOMETER_STATUS_TOTALHOURS = "XCat_OdometerStatusTotalHours"

ATTR_WIFI_STATUS_ISPCHECK = "XCat_WifiStatusIspCheck"
ATTR_WIFI_STATUS_RSSIANTENNADIVERSITY = "XCat_WifiStatusRssiAntennaDiversity"


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
    Mystery = 19


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


class Dryer(Appliance):
    Kind: ApplianceKind = ApplianceKind.Dryer

    @staticmethod
    def wants(appliance_data: ApplianceData) -> bool:
        return (
            "dryer" in appliance_data.data_model.lower()
            and "washer" not in appliance_data.data_model.lower()
        )

    def get_machine_state(self) -> MachineState:
        state_raw = self.get_attribute(ATTR_MACHINE_STATE)
        for k, v in MACHINE_STATE_MAP.items():
            if v == state_raw:
                return k
        return None

    def get_machine_state_value(self) -> int:
        return int(self.get_attribute(ATTR_MACHINE_STATE))

    def get_op_status_dooropen(self) -> bool:
        return self.attr_value_to_bool(self.get_attribute(ATTR_OP_STATUS_DOOROPEN))

    def get_time_status_est_time_remaining(self) -> int:
        return int(self.get_attribute(ATTR_TIME_STATUS_ESTTIMEREMAINING))

    def get_drum_light_on(self) -> bool:
        return self.attr_value_to_bool(self.get_attribute(ATTR_DISPLAY_SET_DRUMLIGHTON))

    def get_change_status_extrapowerchangeable(self) -> bool:
        return self.attr_value_to_bool(
            self.get_attribute(ATTR_CHANGE_STATUS_EXTRAPOWERCHANGEABLE)
        )

    def get_change_status_steamchangeable(self) -> bool:
        return self.attr_value_to_bool(
            self.get_attribute(ATTR_CHANGE_STATUS_STEAMCHANGEABLE)
        )

    def get_change_status_cycleselect(self) -> int:
        return int(self.get_attribute(ATTR_CHANGE_STATUS_CYCLESELECT))

    def get_change_status_dryness(self) -> bool:
        return self.attr_value_to_bool(
            self.get_attribute(ATTR_CHANGE_STATUS_DRYNESS)
        )

    def get_change_status_manualdrytime(self) -> int:
        return int(self.get_attribute(ATTR_CHANGE_STATUS_MANUALDRYTIME))

    def get_change_status_staticguard(self) -> bool:
        return self.attr_value_to_bool(
            self.get_attribute(ATTR_CHANGE_STATUS_STATICGUARD)
        )

    def get_change_status_temperature(self) -> int:
        return int(self.get_attribute(ATTR_CHANGE_STATUS_TEMPERATURE))

    def get_change_status_wrinkleshield(self) -> bool:
        return self.attr_value_to_bool(
            self.get_attribute(ATTR_CHANGE_STATUS_WRINKLESHIELD)
        )

    def get_dryness(self) -> int:
        return int(self.get_attribute(ATTR_CYCLE_SET_DRYNESS))

    def get_manual_dry_time(self) -> int:
        return int(self.get_attribute(ATTR_CYCLE_SET_MANUALDRYTIME))

    def get_cycle_select(self) -> int:
        return int(self.get_attribute(ATTR_CYCLE_SET_CYCLESELECT))

    def get_cycle_status_airflow_status(self) -> bool:
        return self.attr_value_to_bool(
            self.get_attribute(ATTR_CYCLE_STATUS_AIRFLOWSTATUS)
        )

    def get_cycle_status_cool_down(self) -> bool:
        return self.attr_value_to_bool(
            self.get_attribute(ATTR_CYCLE_STATUS_COOLDOWN)
        )

    def get_cycle_status_damp(self) -> bool:
        return self.attr_value_to_bool(
            self.get_attribute(ATTR_CYCLE_STATUS_DAMP)
        )

    def get_cycle_status_drying(self) -> bool:
        return self.attr_value_to_bool(
            self.get_attribute(ATTR_CYCLE_STATUS_DRYING)
        )

    def get_cycle_status_limited_cycle(self) -> bool:
        return self.attr_value_to_bool(
            self.get_attribute(ATTR_CYCLE_STATUS_LIMITEDCYCLE)
        )

    def get_cycle_status_sensing(self) -> bool:
        return self.attr_value_to_bool(
            self.get_attribute(ATTR_CYCLE_STATUS_SENSING)
        )

    def get_cycle_status_static_reduce(self) -> bool:
        return self.attr_value_to_bool(
            self.get_attribute(ATTR_CYCLE_STATUS_STATICREDUCE)
        )

    def get_cycle_status_steaming(self) -> bool:
        return self.attr_value_to_bool(
            self.get_attribute(ATTR_CYCLE_STATUS_STEAMING)
        )

    def get_cycle_status_wet(self) -> bool:
        return self.attr_value_to_bool(
            self.get_attribute(ATTR_CYCLE_STATUS_WET)
        )

    def get_odometer_status_cycle_count(self) -> int:
        return int(self.get_attribute(ATTR_ODOMETER_STATUS_CYCLECOUNT))

    def get_odometer_status_running_hours(self) -> int:
        return int(self.get_attribute(ATTR_ODOMETER_STATUS_RUNNINGHOURS))

    def get_odometer_status_total_hours(self) -> int:
        return int(self.get_attribute(ATTR_ODOMETER_STATUS_TOTALHOURS))

    def get_wifi_status_isp_check(self) -> bool:
        return self.attr_value_to_bool(
            self.get_attribute(ATTR_WIFI_STATUS_ISPCHECK)
        )

    def get_wifi_status_rssi_antenna_diversity(self) -> int:
        return int(self.get_attribute(ATTR_WIFI_STATUS_RSSIANTENNADIVERSITY))

    def get_damp_notification_tone_volume(self) -> int:
        return int(self.get_attribute(ATTR_OP_SET_DAMPNOTIFICATIONTONEVOLUME))

    def get_alert_tone_volume(self) -> int:
        return int(self.get_attribute(ATTR_OP_SET_ALERTTONEVOLUME))

    def get_temperature(self) -> int:
        return int(self.get_attribute(ATTR_CYCLE_SET_TEMPERATURE))

    def get_wrinkle_shield(self) -> int:
        return int(self.get_attribute(ATTR_CYCLE_SET_WRINKLESHIELD))

