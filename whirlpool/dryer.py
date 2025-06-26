from enum import Enum

from .appliance import Appliance

# Machine State
ATTR_MACHINE_STATE = "Cavity_CycleStatusMachineState"

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
ATTRVAL_MACHINE_STATE_CANCELLED = "19"

ATTR_DOOR_OPEN = "Cavity_OpStatusDoorOpen"
ATTR_TIME_REMAINING = "Cavity_TimeStatusEstTimeRemaining"
ATTR_DRUM_LIGHT_ON = "Cavity_DisplaySetDrumLightOn"

ATTR_EXTRA_POWER_CHANGEABLE = "Cavity_ChangeStatusExtraPowerChangeable"
ATTR_STEAM_CHANGEABLE = "Cavity_ChangeStatusSteamChangeable"
ATTR_CYCLE_CHANGEABLE = "DryCavity_ChangeStatusCycleSelect"
ATTR_DRYNESS_CHANGEABLE = "DryCavity_ChangeStatusDryness"
ATTR_MANUAL_DRY_TIME_CHANGEABLE = "DryCavity_ChangeStatusManualDryTime"
ATTR_STATIC_GUARD_CHANGEABLE = "DryCavity_ChangeStatusStaticGuard"
ATTR_TEMPERATURE_CHANGEABLE = "DryCavity_ChangeStatusTemperature"
ATTR_WRINKLE_SHIELD_CHANGEABLE = "DryCavity_ChangeStatusWrinkleShield"

ATTR_CYCLE = "DryCavity_CycleSetCycleSelect"

ATTRVAL_CYCLE_REGULAR = "1"
ATTRVAL_CYCLE_HEAVY_DUTY = "2"
ATTRVAL_CYCLE_DENIM = "3"
ATTRVAL_CYCLE_DELICATES = "4"
ATTRVAL_CYCLE_WRINKLE_CONTROL = "5"
ATTRVAL_CYCLE_BULKY_ITEMS = "6"
ATTRVAL_CYCLE_QUICK_DRY = "7"
ATTRVAL_CYCLE_SANITIZE = "9"
ATTRVAL_CYCLE_STEAM_REFRESH = "10"
ATTRVAL_CYCLE_TIMED_DRY = "11"
ATTRVAL_CYCLE_COLORS_BRIGHTS = "13"
ATTRVAL_CYCLE_TOWELS = "15"
ATTRVAL_CYCLE_WHITES = "16"
ATTRVAL_CYCLE_NORMAL = "41"

ATTR_DRYNESS = "DryCavity_CycleSetDryness"

ATTRVAL_DRYNESS_LOW = "0"
ATTRVAL_DRYNESS_LESS = "1"
ATTRVAL_DRYNESS_NORMAL = "4"
ATTRVAL_DRYNESS_MORE = "7"
ATTRVAL_DRYNESS_HIGH = "10"

ATTR_MANUAL_DRY_TIME = "DryCavity_CycleSetManualDryTime"

ATTR_TEMPERATURE = "DryCavity_CycleSetTemperature"

ATTRVAL_TEMPERATURE_AIR = "0"
ATTRVAL_TEMPERATURE_COOL = "2"
ATTRVAL_TEMPERATURE_WARM = "5"
ATTRVAL_TEMPERATURE_WARM_HIGH = "6"
ATTRVAL_TEMPERATURE_HOT = "8"

ATTR_WRINKLE_SHIELD = "DryCavity_CycleSetWrinkleShield"

ATTRVAL_WRINKLE_SHIELD_OFF = "0"
ATTRVAL_WRINKLE_SHIELD_ON = "1"
ATTRVAL_WRINKLE_SHIELD_ON_WITH_STEAM = "2"

ATTR_CYCLE_STATUS_AIR_FLOW_STATUS = "DryCavity_CycleStatusAirFlowStatus"
ATTR_CYCLE_STATUS_COOL_DOWN = "DryCavity_CycleStatusCoolDown"
ATTR_CYCLE_STATUS_DAMP = "DryCavity_CycleStatusDamp"
ATTR_CYCLE_STATUS_DRYING = "DryCavity_CycleStatusDrying"
ATTR_CYCLE_STATUS_LIMITED_CYCLE = "DryCavity_CycleStatusLimitedCycle"
ATTR_CYCLE_STATUS_SENSING = "DryCavity_CycleStatusSensing"
ATTR_CYCLE_STATUS_STATIC_REDUCE = "DryCavity_CycleStatusStaticReduce"
ATTR_CYCLE_STATUS_STEAMING = "DryCavity_CycleStatusSteaming"
ATTR_CYCLE_STATUS_WET = "DryCavity_CycleStatusWet"

ATTR_DAMP_NOTIFICATION_TONE_VOLUME = "DrySys_OpSetDampNotificationToneVolume"
ATTR_ALERT_TONE_VOLUME = "Sys_OpSetAlertToneVolume"
ATTR_CYCLE_COUNT = "XCat_OdometerStatusCycleCount"


class Cycle(Enum):
    Regular = 1
    HeavyDuty = 2
    Denim = 3
    Delicates = 4
    WrinkleControl = 5
    BulkyItems = 6
    QuickDry = 7
    Sanitize = 9
    SteamRefresh = 10
    TimedDry = 11
    ColorsBrights = 13
    Towels = 15
    Whites = 16
    Normal = 41


CYCLE_MAP = {
    ATTRVAL_CYCLE_REGULAR: Cycle.Regular,
    ATTRVAL_CYCLE_HEAVY_DUTY: Cycle.HeavyDuty,
    ATTRVAL_CYCLE_DENIM: Cycle.Denim,
    ATTRVAL_CYCLE_DELICATES: Cycle.Delicates,
    ATTRVAL_CYCLE_WRINKLE_CONTROL: Cycle.WrinkleControl,
    ATTRVAL_CYCLE_BULKY_ITEMS: Cycle.BulkyItems,
    ATTRVAL_CYCLE_QUICK_DRY: Cycle.QuickDry,
    ATTRVAL_CYCLE_SANITIZE: Cycle.Sanitize,
    ATTRVAL_CYCLE_STEAM_REFRESH: Cycle.SteamRefresh,
    ATTRVAL_CYCLE_TIMED_DRY: Cycle.TimedDry,
    ATTRVAL_CYCLE_COLORS_BRIGHTS: Cycle.ColorsBrights,
    ATTRVAL_CYCLE_TOWELS: Cycle.Towels,
    ATTRVAL_CYCLE_WHITES: Cycle.Whites,
    ATTRVAL_CYCLE_NORMAL: Cycle.Normal,
}


class Dryness(Enum):
    Low = 0
    Less = 1
    Normal = 4
    More = 7
    High = 10


DRYNESS_MAP = {
    ATTRVAL_DRYNESS_LOW: Dryness.Low,
    ATTRVAL_DRYNESS_LESS: Dryness.Less,
    ATTRVAL_DRYNESS_NORMAL: Dryness.Normal,
    ATTRVAL_DRYNESS_MORE: Dryness.More,
    ATTRVAL_DRYNESS_HIGH: Dryness.High,
}


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
    Cancelled = 19


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


class Temperature(Enum):
    Air = 0
    Cool = 2
    Warm = 5
    WarmHigh = 6
    Hot = 8


TEMPERATURE_MAP = {
    ATTRVAL_TEMPERATURE_AIR: Temperature.Air,
    ATTRVAL_TEMPERATURE_COOL: Temperature.Cool,
    ATTRVAL_TEMPERATURE_WARM: Temperature.Warm,
    ATTRVAL_TEMPERATURE_WARM_HIGH: Temperature.WarmHigh,
    ATTRVAL_TEMPERATURE_HOT: Temperature.Hot,
}


class WrinkleShield(Enum):
    Off = 0
    On = 1
    OnWithSteam = 2


WRINKLE_SHIELD_MAP = {
    ATTRVAL_WRINKLE_SHIELD_OFF: WrinkleShield.Off,
    ATTRVAL_WRINKLE_SHIELD_ON: WrinkleShield.On,
    ATTRVAL_WRINKLE_SHIELD_ON_WITH_STEAM: WrinkleShield.OnWithSteam,
}


class Dryer(Appliance):
    def get_machine_state(self) -> MachineState | None:
        state_raw = self._get_attribute(ATTR_MACHINE_STATE)
        if state_raw is None:
            return None
        return MACHINE_STATE_MAP.get(state_raw, None)

    def get_door_open(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_DOOR_OPEN))

    def get_time_remaining(self) -> int | None:
        return self._get_int_attribute(ATTR_TIME_REMAINING)

    def get_drum_light_on(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_DRUM_LIGHT_ON))

    def get_extra_power_changeable(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_EXTRA_POWER_CHANGEABLE))

    def get_steam_changeable(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_STEAM_CHANGEABLE))

    def get_cycle_changeable(self) -> int | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_CYCLE_CHANGEABLE))

    def get_dryness_changeable(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_DRYNESS_CHANGEABLE))

    def get_manual_dry_time_changeable(self) -> int | None:
        return self.attr_value_to_bool(
            self._get_attribute(ATTR_MANUAL_DRY_TIME_CHANGEABLE)
        )

    def get_static_guard_changeable(self) -> bool | None:
        return self.attr_value_to_bool(
            self._get_attribute(ATTR_STATIC_GUARD_CHANGEABLE)
        )

    def get_temperature_changeable(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_TEMPERATURE_CHANGEABLE))

    def get_wrinkle_shield_changeable(self) -> bool | None:
        return self.attr_value_to_bool(
            self._get_attribute(ATTR_WRINKLE_SHIELD_CHANGEABLE)
        )

    def get_dryness(self) -> Dryness | None:
        dryness_raw = self._get_attribute(ATTR_DRYNESS)
        if dryness_raw is None:
            return None
        return DRYNESS_MAP.get(dryness_raw, None)

    def get_manual_dry_time(self) -> int | None:
        return self._get_int_attribute(ATTR_MANUAL_DRY_TIME)

    def get_cycle(self) -> Cycle | None:
        cycle_raw = self._get_attribute(ATTR_CYCLE)
        if cycle_raw is None:
            return None
        return CYCLE_MAP.get(cycle_raw, None)

    def get_cycle_status_airflow_status(self) -> bool | None:
        return self.attr_value_to_bool(
            self._get_attribute(ATTR_CYCLE_STATUS_AIR_FLOW_STATUS)
        )

    def get_cycle_status_cool_down(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_CYCLE_STATUS_COOL_DOWN))

    def get_cycle_status_damp(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_CYCLE_STATUS_DAMP))

    def get_cycle_status_drying(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_CYCLE_STATUS_DRYING))

    def get_cycle_status_limited_cycle(self) -> bool | None:
        return self.attr_value_to_bool(
            self._get_attribute(ATTR_CYCLE_STATUS_LIMITED_CYCLE)
        )

    def get_cycle_status_sensing(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_CYCLE_STATUS_SENSING))

    def get_cycle_status_static_reduce(self) -> bool | None:
        return self.attr_value_to_bool(
            self._get_attribute(ATTR_CYCLE_STATUS_STATIC_REDUCE)
        )

    def get_cycle_status_steaming(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_CYCLE_STATUS_STEAMING))

    def get_cycle_status_wet(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_CYCLE_STATUS_WET))

    def get_cycle_count(self) -> int | None:
        return self._get_int_attribute(ATTR_CYCLE_COUNT)

    def get_damp_notification_tone_volume(self) -> int | None:
        return self._get_int_attribute(ATTR_DAMP_NOTIFICATION_TONE_VOLUME)

    def get_alert_tone_volume(self) -> int | None:
        return self._get_int_attribute(ATTR_ALERT_TONE_VOLUME)

    def get_temperature(self) -> Temperature | None:
        temperature_raw = self._get_attribute(ATTR_TEMPERATURE)
        if temperature_raw is None:
            return None
        return TEMPERATURE_MAP.get(temperature_raw, None)

    def get_wrinkle_shield(self) -> WrinkleShield | None:
        shield_raw = self._get_attribute(ATTR_WRINKLE_SHIELD)
        if shield_raw is None:
            return None
        return WRINKLE_SHIELD_MAP.get(shield_raw, None)
