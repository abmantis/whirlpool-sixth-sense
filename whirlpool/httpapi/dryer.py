import logging

from ..dryer import (
    Cycle,
    Dryness,
    MachineState,
    Temperature,
    WrinkleShield,
)
from ..dryer import Dryer as BaseDryer
from .appliance import Appliance

LOGGER = logging.getLogger(__name__)

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
ATTR_REMOTE_CONTROL_ENABLE = "XCat_RemoteSetRemoteControlEnable"
ATTR_OPERATIONS = "Cavity_OpSetOperations"

OPERATION_CANCEL = "1"
OPERATION_START = "2"
OPERATION_PAUSE = "5"
OPERATION_RESUME = "6"

ATTR_EXTRA_POWER_CHANGEABLE = "Cavity_ChangeStatusExtraPowerChangeable"
ATTR_STEAM_CHANGEABLE = "Cavity_ChangeStatusSteamChangeable"
ATTR_CYCLE_CHANGEABLE = "DryCavity_ChangeStatusCycleSelect"
ATTR_DRYNESS_CHANGEABLE = "DryCavity_ChangeStatusDryness"
ATTR_MANUAL_DRY_TIME_CHANGEABLE = "DryCavity_ChangeStatusManualDryTime"
ATTR_STATIC_GUARD_CHANGEABLE = "DryCavity_ChangeStatusStaticGuard"
ATTR_ECO_BOOST_CHANGEABLE = "DryCavity_ChangeStatusEcoBoost"
ATTR_TEMPERATURE_CHANGEABLE = "DryCavity_ChangeStatusTemperature"
ATTR_WRINKLE_SHIELD_CHANGEABLE = "DryCavity_ChangeStatusWrinkleShield"

ATTR_CYCLE = "DryCavity_CycleSetCycleSelect"

# Legacy flat cycle values — preserved for model compatibility.
# NOTE: ATTRVAL_CYCLE_DENIM ("3") and ATTRVAL_CYCLE_NORMAL ("41") are NOT
# in the WED9620HBK2 DDM. They may be valid on other dryer models. Do not
# delete them globally; model-gate any WED9620HBK2-specific behaviour instead.
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

# Matrix (What+How) cycle values — DDM-proven on WED9620HBK2
# (ccuri=API144_LAUNDRY_V17). All values 17–40 are confirmed from the live DDM
# capture; see Phase 5B-5D analysis artifacts.
ATTRVAL_CYCLE_COLORS_HEAVY_DUTY = "17"
ATTRVAL_CYCLE_COLORS_QUICK = "18"
ATTRVAL_CYCLE_COLORS_SANITIZE = "19"
ATTRVAL_CYCLE_COLORS_TIMED_DRY = "20"
ATTRVAL_CYCLE_COLORS_WRINKLE_CONTROL = "21"
ATTRVAL_CYCLE_BULKY_HEAVY_DUTY = "22"
ATTRVAL_CYCLE_BULKY_QUICK = "23"
ATTRVAL_CYCLE_BULKY_SANITIZE = "24"
ATTRVAL_CYCLE_BULKY_TIMED_DRY = "25"
ATTRVAL_CYCLE_BULKY_WRINKLE_CONTROL = "26"
ATTRVAL_CYCLE_DELICATES_HEAVY_DUTY = "27"
ATTRVAL_CYCLE_DELICATES_QUICK = "28"
# ATTRVAL_CYCLE_DELICATES_SANITIZE intentionally omitted: DDM-forbidden.
ATTRVAL_CYCLE_DELICATES_TIMED_DRY = "29"
ATTRVAL_CYCLE_DELICATES_WRINKLE_CONTROL = "30"
ATTRVAL_CYCLE_TOWELS_HEAVY_DUTY = "31"
ATTRVAL_CYCLE_TOWELS_QUICK = "32"
ATTRVAL_CYCLE_TOWELS_SANITIZE = "33"
ATTRVAL_CYCLE_TOWELS_TIMED_DRY = "34"
ATTRVAL_CYCLE_TOWELS_WRINKLE_CONTROL = "35"
ATTRVAL_CYCLE_WHITES_HEAVY_DUTY = "36"
ATTRVAL_CYCLE_WHITES_QUICK = "37"
ATTRVAL_CYCLE_WHITES_SANITIZE = "38"
ATTRVAL_CYCLE_WHITES_TIMED_DRY = "39"
ATTRVAL_CYCLE_WHITES_WRINKLE_CONTROL = "40"

ATTR_DRYNESS = "DryCavity_CycleSetDryness"

# ATTRVAL_DRYNESS_LOW ("0") is preserved for model compatibility but is NOT
# in the WED9620HBK2 DDM. ATTRVAL_DRYNESS_HIGH ("10") maps to DDM label
# "None" on WED9620HBK2; see DRYNESS_DISPLAY below.
ATTRVAL_DRYNESS_LOW = "0"
ATTRVAL_DRYNESS_LESS = "1"
ATTRVAL_DRYNESS_NORMAL = "4"
ATTRVAL_DRYNESS_MORE = "7"
ATTRVAL_DRYNESS_HIGH = "10"

ATTR_MANUAL_DRY_TIME = "DryCavity_CycleSetManualDryTime"

ATTR_TEMPERATURE = "DryCavity_CycleSetTemperature"

# DDM-proven temperature values for WED9620HBK2.
# ATTRVAL_TEMPERATURE_COOL_LOW ("1") is new; ATTRVAL_TEMPERATURE_WARM_HIGH ("6")
# is NOT in the WED9620HBK2 DDM — preserved for other model compatibility.
ATTRVAL_TEMPERATURE_AIR = "0"
ATTRVAL_TEMPERATURE_COOL_LOW = "1"
ATTRVAL_TEMPERATURE_COOL = "2"
ATTRVAL_TEMPERATURE_WARM = "5"
ATTRVAL_TEMPERATURE_WARM_HIGH = "6"
ATTRVAL_TEMPERATURE_HOT = "8"

ATTR_WRINKLE_SHIELD = "DryCavity_CycleSetWrinkleShield"

ATTRVAL_WRINKLE_SHIELD_OFF = "0"
ATTRVAL_WRINKLE_SHIELD_ON = "1"
ATTRVAL_WRINKLE_SHIELD_ON_WITH_STEAM = "2"

ATTR_STATIC_GUARD = "DryCavity_CycleSetStaticGuardEnable"
ATTR_ECO_BOOST = "DryCavity_CycleSetEcoBoostEnable"

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
    # Matrix cycles
    ATTRVAL_CYCLE_COLORS_HEAVY_DUTY: Cycle.ColorsHeavyDuty,
    ATTRVAL_CYCLE_COLORS_QUICK: Cycle.ColorsQuick,
    ATTRVAL_CYCLE_COLORS_SANITIZE: Cycle.ColorsSanitize,
    ATTRVAL_CYCLE_COLORS_TIMED_DRY: Cycle.ColorsTimedDry,
    ATTRVAL_CYCLE_COLORS_WRINKLE_CONTROL: Cycle.ColorsWrinkleControl,
    ATTRVAL_CYCLE_BULKY_HEAVY_DUTY: Cycle.BulkyHeavyDuty,
    ATTRVAL_CYCLE_BULKY_QUICK: Cycle.BulkyQuick,
    ATTRVAL_CYCLE_BULKY_SANITIZE: Cycle.BulkySanitize,
    ATTRVAL_CYCLE_BULKY_TIMED_DRY: Cycle.BulkyTimedDry,
    ATTRVAL_CYCLE_BULKY_WRINKLE_CONTROL: Cycle.BulkyWrinkleControl,
    ATTRVAL_CYCLE_DELICATES_HEAVY_DUTY: Cycle.DelicatesHeavyDuty,
    ATTRVAL_CYCLE_DELICATES_QUICK: Cycle.DelicatesQuick,
    ATTRVAL_CYCLE_DELICATES_TIMED_DRY: Cycle.DelicatesTimedDry,
    ATTRVAL_CYCLE_DELICATES_WRINKLE_CONTROL: Cycle.DelicatesWrinkleControl,
    ATTRVAL_CYCLE_TOWELS_HEAVY_DUTY: Cycle.TowelsHeavyDuty,
    ATTRVAL_CYCLE_TOWELS_QUICK: Cycle.TowelsQuick,
    ATTRVAL_CYCLE_TOWELS_SANITIZE: Cycle.TowelsSanitize,
    ATTRVAL_CYCLE_TOWELS_TIMED_DRY: Cycle.TowelsTimedDry,
    ATTRVAL_CYCLE_TOWELS_WRINKLE_CONTROL: Cycle.TowelsWrinkleControl,
    ATTRVAL_CYCLE_WHITES_HEAVY_DUTY: Cycle.WhitesHeavyDuty,
    ATTRVAL_CYCLE_WHITES_QUICK: Cycle.WhitesQuick,
    ATTRVAL_CYCLE_WHITES_SANITIZE: Cycle.WhitesSanitize,
    ATTRVAL_CYCLE_WHITES_TIMED_DRY: Cycle.WhitesTimedDry,
    ATTRVAL_CYCLE_WHITES_WRINKLE_CONTROL: Cycle.WhitesWrinkleControl,
}

# What+How → wire value mapping for WED9620HBK2 matrix cycles.
# All entries are DDM-proven; ("delicates", "sanitize") is intentionally absent
# — it is DDM-forbidden and is explicitly blocked in set_dry_cycle_pair().
DRY_CYCLE_PAIR_MAP: dict[tuple[str, str], str] = {
    ("regular", "normal"): ATTRVAL_CYCLE_REGULAR,
    ("regular", "heavy_duty"): ATTRVAL_CYCLE_HEAVY_DUTY,
    ("regular", "wrinkle_control"): ATTRVAL_CYCLE_WRINKLE_CONTROL,
    ("regular", "quick"): ATTRVAL_CYCLE_QUICK_DRY,
    ("regular", "sanitize"): ATTRVAL_CYCLE_SANITIZE,
    ("regular", "timed_dry"): ATTRVAL_CYCLE_TIMED_DRY,
    ("colors", "normal"): ATTRVAL_CYCLE_COLORS_BRIGHTS,
    ("colors", "heavy_duty"): ATTRVAL_CYCLE_COLORS_HEAVY_DUTY,
    ("colors", "quick"): ATTRVAL_CYCLE_COLORS_QUICK,
    ("colors", "sanitize"): ATTRVAL_CYCLE_COLORS_SANITIZE,
    ("colors", "timed_dry"): ATTRVAL_CYCLE_COLORS_TIMED_DRY,
    ("colors", "wrinkle_control"): ATTRVAL_CYCLE_COLORS_WRINKLE_CONTROL,
    ("bulky", "normal"): ATTRVAL_CYCLE_BULKY_ITEMS,
    ("bulky", "heavy_duty"): ATTRVAL_CYCLE_BULKY_HEAVY_DUTY,
    ("bulky", "quick"): ATTRVAL_CYCLE_BULKY_QUICK,
    ("bulky", "sanitize"): ATTRVAL_CYCLE_BULKY_SANITIZE,
    ("bulky", "timed_dry"): ATTRVAL_CYCLE_BULKY_TIMED_DRY,
    ("bulky", "wrinkle_control"): ATTRVAL_CYCLE_BULKY_WRINKLE_CONTROL,
    ("delicates", "normal"): ATTRVAL_CYCLE_DELICATES,
    ("delicates", "heavy_duty"): ATTRVAL_CYCLE_DELICATES_HEAVY_DUTY,
    ("delicates", "quick"): ATTRVAL_CYCLE_DELICATES_QUICK,
    # ("delicates", "sanitize") intentionally absent — DDM-forbidden
    ("delicates", "timed_dry"): ATTRVAL_CYCLE_DELICATES_TIMED_DRY,
    ("delicates", "wrinkle_control"): ATTRVAL_CYCLE_DELICATES_WRINKLE_CONTROL,
    ("towels", "normal"): ATTRVAL_CYCLE_TOWELS,
    ("towels", "heavy_duty"): ATTRVAL_CYCLE_TOWELS_HEAVY_DUTY,
    ("towels", "quick"): ATTRVAL_CYCLE_TOWELS_QUICK,
    ("towels", "sanitize"): ATTRVAL_CYCLE_TOWELS_SANITIZE,
    ("towels", "timed_dry"): ATTRVAL_CYCLE_TOWELS_TIMED_DRY,
    ("towels", "wrinkle_control"): ATTRVAL_CYCLE_TOWELS_WRINKLE_CONTROL,
    ("whites", "normal"): ATTRVAL_CYCLE_WHITES,
    ("whites", "heavy_duty"): ATTRVAL_CYCLE_WHITES_HEAVY_DUTY,
    ("whites", "quick"): ATTRVAL_CYCLE_WHITES_QUICK,
    ("whites", "sanitize"): ATTRVAL_CYCLE_WHITES_SANITIZE,
    ("whites", "timed_dry"): ATTRVAL_CYCLE_WHITES_TIMED_DRY,
    ("whites", "wrinkle_control"): ATTRVAL_CYCLE_WHITES_WRINKLE_CONTROL,
}

# Reverse map: wire value → (what, how). Derived from DRY_CYCLE_PAIR_MAP.
DRY_CYCLE_PAIR_REVERSE: dict[str, tuple[str, str]] = {
    v: k for k, v in DRY_CYCLE_PAIR_MAP.items()
}

# Utility cycles: standalone cycle modes outside the What+How matrix.
# DDM-proven on WED9620HBK2: CycleSelect=10 → Steam Refresh.
# This is distinct from WrinkleShield=2 (On with Steam), which is a
# post-cycle option — not a wash/dry cycle.
UTILITY_CYCLE_MAP: dict[str, str] = {
    "steam_refresh": ATTRVAL_CYCLE_STEAM_REFRESH,
}
UTILITY_CYCLE_REVERSE: dict[str, str] = {v: k for k, v in UTILITY_CYCLE_MAP.items()}

# --- Manual Dry Time (MDT) cycle groups ---
# Only cycles in one of these two groups support MDT selection.
# Each group has exactly 6 members (DDM-proven on WED9620HBK2).
# Live evidence: ChangeStatusManualDryTime="1" has been observed while the
# active cycle was TowelsHeavyDuty (wire "31"), a non-MDT cycle.  The
# changeable gate alone is therefore insufficient; the cycle-group check is
# mandatory and must be applied independently.
QUICK_GROUP_CYCLES: frozenset[str] = frozenset(
    {
        ATTRVAL_CYCLE_QUICK_DRY,  # "7"
        ATTRVAL_CYCLE_COLORS_QUICK,  # "18"
        ATTRVAL_CYCLE_BULKY_QUICK,  # "23"
        ATTRVAL_CYCLE_DELICATES_QUICK,  # "28"
        ATTRVAL_CYCLE_TOWELS_QUICK,  # "32"
        ATTRVAL_CYCLE_WHITES_QUICK,  # "37"
    }
)

TIMED_DRY_GROUP_CYCLES: frozenset[str] = frozenset(
    {
        ATTRVAL_CYCLE_TIMED_DRY,  # "11"
        ATTRVAL_CYCLE_COLORS_TIMED_DRY,  # "20"
        ATTRVAL_CYCLE_BULKY_TIMED_DRY,  # "25"
        ATTRVAL_CYCLE_DELICATES_TIMED_DRY,  # "29"
        ATTRVAL_CYCLE_TOWELS_TIMED_DRY,  # "34"
        ATTRVAL_CYCLE_WHITES_TIMED_DRY,  # "39"
    }
)

# Allowed wire values (seconds) per group.
# Quick: 15 min, 30 min, 45 min.
# Timed Dry: 30 min, 60 min, 90 min.
# (DDM-proven on WED9620HBK2; see Phase 5B-5D analysis artifacts.)
QUICK_MDT_ALLOWED_SECONDS: frozenset[str] = frozenset({"900", "1800", "2700"})
TIMED_DRY_MDT_ALLOWED_SECONDS: frozenset[str] = frozenset({"1800", "3600", "5400"})


DRYNESS_MAP = {
    ATTRVAL_DRYNESS_LOW: Dryness.Low,
    ATTRVAL_DRYNESS_LESS: Dryness.Less,
    ATTRVAL_DRYNESS_NORMAL: Dryness.Normal,
    ATTRVAL_DRYNESS_MORE: Dryness.More,
    ATTRVAL_DRYNESS_HIGH: Dryness.High,
}

# String keys used by set_dryness() and get_dryness_str().
# Wire value "10" is DDM-labeled "None" on WED9620HBK2; the option key is
# "none" accordingly. Low ("0") is not DDM-proven for WED9620HBK2.
DRYNESS_SET_VALUES: dict[str, str] = {
    "less": ATTRVAL_DRYNESS_LESS,
    "normal": ATTRVAL_DRYNESS_NORMAL,
    "more": ATTRVAL_DRYNESS_MORE,
    "none": ATTRVAL_DRYNESS_HIGH,
}
DRYNESS_DISPLAY: dict[str, str] = {
    ATTRVAL_DRYNESS_LESS: "less",
    ATTRVAL_DRYNESS_NORMAL: "normal",
    ATTRVAL_DRYNESS_MORE: "more",
    ATTRVAL_DRYNESS_HIGH: "none",
}


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


TEMPERATURE_MAP = {
    ATTRVAL_TEMPERATURE_AIR: Temperature.Air,
    ATTRVAL_TEMPERATURE_COOL_LOW: Temperature.CoolLow,
    ATTRVAL_TEMPERATURE_COOL: Temperature.Cool,
    ATTRVAL_TEMPERATURE_WARM: Temperature.Warm,
    ATTRVAL_TEMPERATURE_WARM_HIGH: Temperature.WarmHigh,
    ATTRVAL_TEMPERATURE_HOT: Temperature.Hot,
}

# String keys used by set_temperature() and get_temperature_str().
# Names reflect WED9620HBK2 DDM labels (CoolMid, WarmMid, HotMid).
# WarmHigh ("6") is not DDM-proven for WED9620HBK2 — no display key for it.
TEMPERATURE_SET_VALUES: dict[str, str] = {
    "air": ATTRVAL_TEMPERATURE_AIR,
    "cool_low": ATTRVAL_TEMPERATURE_COOL_LOW,
    "cool_mid": ATTRVAL_TEMPERATURE_COOL,
    "warm_mid": ATTRVAL_TEMPERATURE_WARM,
    "hot_mid": ATTRVAL_TEMPERATURE_HOT,
}
TEMPERATURE_DISPLAY: dict[str, str] = {
    ATTRVAL_TEMPERATURE_AIR: "air",
    ATTRVAL_TEMPERATURE_COOL_LOW: "cool_low",
    ATTRVAL_TEMPERATURE_COOL: "cool_mid",
    ATTRVAL_TEMPERATURE_WARM: "warm_mid",
    ATTRVAL_TEMPERATURE_HOT: "hot_mid",
    # ATTRVAL_TEMPERATURE_WARM_HIGH ("6") intentionally absent — not DDM-proven
}


WRINKLE_SHIELD_MAP = {
    ATTRVAL_WRINKLE_SHIELD_OFF: WrinkleShield.Off,
    ATTRVAL_WRINKLE_SHIELD_ON: WrinkleShield.On,
    ATTRVAL_WRINKLE_SHIELD_ON_WITH_STEAM: WrinkleShield.OnWithSteam,
}

# String keys used by set_wrinkle_shield(); values are the wire strings.
# DDM-proven on WED9620HBK2: DryCavity_ChangeStatusWrinkleShield="1" (changeable);
# DryCavity_CycleSetWrinkleShield="0" at Setting state; Steam accessible via
# Cavity_ChangeStatusSteamChangeable="1" co-present in the same DDM capture.
WRINKLE_SHIELD_SET_VALUES = {
    "off": ATTRVAL_WRINKLE_SHIELD_OFF,
    "on": ATTRVAL_WRINKLE_SHIELD_ON,
    "on_with_steam": ATTRVAL_WRINKLE_SHIELD_ON_WITH_STEAM,
}

WRINKLE_SHIELD_DISPLAY = {
    WrinkleShield.Off: "off",
    WrinkleShield.On: "on",
    WrinkleShield.OnWithSteam: "on_with_steam",
}

# String keys for Static Guard and Eco Boost (on/off boolean DDM attributes).
STATIC_GUARD_SET_VALUES: dict[str, str] = {"off": "0", "on": "1"}
STATIC_GUARD_DISPLAY: dict[str, str] = {"0": "off", "1": "on"}
ECO_BOOST_SET_VALUES: dict[str, str] = {"off": "0", "on": "1"}
ECO_BOOST_DISPLAY: dict[str, str] = {"0": "off", "1": "on"}


class Dryer(BaseDryer, Appliance):
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

    def get_eco_boost_changeable(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_ECO_BOOST_CHANGEABLE))

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

    def get_dryness_str(self) -> str | None:
        """Return current dryness as an option key for HA selects."""
        raw = self._get_attribute(ATTR_DRYNESS)
        if raw is None:
            return None
        return DRYNESS_DISPLAY.get(raw)

    def get_manual_dry_time(self) -> int | None:
        return self._get_int_attribute(ATTR_MANUAL_DRY_TIME)

    def get_manual_dry_time_options_minutes(self) -> list[str] | None:
        """Return the allowed MDT option keys (in minutes) for the current cycle.

        Returns:
            ``["15", "30", "45"]``  for a Quick-group cycle,
            ``["30", "60", "90"]``  for a Timed-Dry-group cycle,
            ``None``                for any other cycle (missing, unknown,
                                    or a known non-MDT cycle).

        Callers must treat ``None`` as "MDT not applicable" and must NOT
        expose MDT options or send MDT commands when this returns ``None``.
        The ChangeStatus gate alone is insufficient — live evidence shows
        ChangeStatusManualDryTime="1" while a non-MDT cycle is active.
        """
        cycle_raw = self._get_attribute(ATTR_CYCLE)
        if cycle_raw in QUICK_GROUP_CYCLES:
            return ["15", "30", "45"]
        if cycle_raw in TIMED_DRY_GROUP_CYCLES:
            return ["30", "60", "90"]
        return None

    def get_cycle(self) -> Cycle | None:
        cycle_raw = self._get_attribute(ATTR_CYCLE)
        if cycle_raw is None:
            return None
        return CYCLE_MAP.get(cycle_raw, None)

    def get_dry_cycle_pair(self) -> tuple[str, str] | None:
        """Return the current (what, how) pair for matrix cycles, or None.

        Returns None if no data has been fetched, or if the current cycle is
        not part of the What+How matrix (e.g. it is a utility cycle such as
        Steam Refresh).
        """
        cycle_raw = self._get_attribute(ATTR_CYCLE)
        if cycle_raw is None:
            return None
        return DRY_CYCLE_PAIR_REVERSE.get(cycle_raw)

    def get_utility_cycle(self) -> str | None:
        """Return the current utility cycle key ('steam_refresh'), or None.

        Returns None if no data has been fetched, or if the current cycle is
        not a utility cycle.
        """
        cycle_raw = self._get_attribute(ATTR_CYCLE)
        if cycle_raw is None:
            return None
        return UTILITY_CYCLE_REVERSE.get(cycle_raw)

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

    def get_temperature_str(self) -> str | None:
        """Return current temperature as an option key for HA selects."""
        raw = self._get_attribute(ATTR_TEMPERATURE)
        if raw is None:
            return None
        return TEMPERATURE_DISPLAY.get(raw)

    def get_wrinkle_shield(self) -> WrinkleShield | None:
        shield_raw = self._get_attribute(ATTR_WRINKLE_SHIELD)
        if shield_raw is None:
            return None
        return WRINKLE_SHIELD_MAP.get(shield_raw, None)

    def get_wrinkle_shield_str(self) -> str | None:
        """Return current WrinkleShield as a string option key for HA selects."""
        shield = self.get_wrinkle_shield()
        return None if shield is None else WRINKLE_SHIELD_DISPLAY.get(shield)

    def get_static_guard(self) -> bool | None:
        """Return whether Static Guard is enabled, or None if unknown."""
        return self.attr_value_to_bool(self._get_attribute(ATTR_STATIC_GUARD))

    def get_static_guard_str(self) -> str | None:
        """Return current Static Guard state as 'on'/'off' for HA selects."""
        raw = self._get_attribute(ATTR_STATIC_GUARD)
        if raw is None:
            return None
        return STATIC_GUARD_DISPLAY.get(raw)

    def get_eco_boost(self) -> bool | None:
        """Return whether Eco Boost is enabled, or None if unknown."""
        return self.attr_value_to_bool(self._get_attribute(ATTR_ECO_BOOST))

    def get_eco_boost_str(self) -> str | None:
        """Return current Eco Boost state as 'on'/'off' for HA selects."""
        raw = self._get_attribute(ATTR_ECO_BOOST)
        if raw is None:
            return None
        return ECO_BOOST_DISPLAY.get(raw)

    async def set_wrinkle_shield(self, option: str) -> bool:
        """Set WrinkleShield (off / on / on_with_steam).

        All three values are DDM-proven on WED9620HBK2:
          DryCavity_CycleSetWrinkleShield wire key confirmed present;
          DryCavity_ChangeStatusWrinkleShield = "1" (changeable);
          Cavity_ChangeStatusSteamChangeable = "1" (steam accessible via value "2").
        """
        value = WRINKLE_SHIELD_SET_VALUES.get(option)
        if value is None or not self.get_wrinkle_shield_changeable():
            return False
        return await self.send_attributes({ATTR_WRINKLE_SHIELD: value})

    async def set_dryness(self, option: str) -> bool:
        """Set dryness level (less / normal / more / none).

        All four option keys are DDM-proven on WED9620HBK2. 'none' maps to
        wire value "10" (DDM label "None").
        Returns False when DryCavity_ChangeStatusDryness is not True.
        """
        value = DRYNESS_SET_VALUES.get(option)
        if value is None or not self.get_dryness_changeable():
            return False
        return await self.send_attributes({ATTR_DRYNESS: value})

    async def set_temperature(self, option: str) -> bool:
        """Set drying temperature (air / cool_low / cool_mid / warm_mid / hot_mid).

        All five option keys are DDM-proven on WED9620HBK2.
        Returns False when DryCavity_ChangeStatusTemperature is not True.
        """
        value = TEMPERATURE_SET_VALUES.get(option)
        if value is None or not self.get_temperature_changeable():
            return False
        return await self.send_attributes({ATTR_TEMPERATURE: value})

    async def set_dry_cycle_pair(self, what: str, how: str) -> bool:
        """Set cycle by What+How pair.

        Raises ValueError for the DDM-forbidden Delicates+Sanitize combination
        and for unknown (what, how) pairs.
        Returns False when DryCavity_ChangeStatusCycleSelect is not True.
        """
        if what == "delicates" and how == "sanitize":
            raise ValueError(
                "Delicates+Sanitize is not supported on this appliance "
                "(absent from DDM and from the official Whirlpool app)"
            )
        value = DRY_CYCLE_PAIR_MAP.get((what, how))
        if value is None:
            raise ValueError(f"Unknown dry cycle combination: {what!r}/{how!r}")
        if not self.get_cycle_changeable():
            return False
        return await self.send_attributes({ATTR_CYCLE: value})

    async def set_utility_cycle(self, utility: str) -> bool:
        """Set a utility cycle (currently: 'steam_refresh').

        Raises ValueError for unknown utility cycle keys.
        Returns False when DryCavity_ChangeStatusCycleSelect is not True.
        """
        value = UTILITY_CYCLE_MAP.get(utility)
        if value is None:
            raise ValueError(f"Unknown utility cycle: {utility!r}")
        if not self.get_cycle_changeable():
            return False
        return await self.send_attributes({ATTR_CYCLE: value})

    async def set_static_guard(self, option: str) -> bool:
        """Set Static Guard ('off' / 'on').

        Returns False when DryCavity_ChangeStatusStaticGuard is not True or
        when the option key is unrecognised.
        """
        value = STATIC_GUARD_SET_VALUES.get(option)
        if value is None or not self.get_static_guard_changeable():
            return False
        return await self.send_attributes({ATTR_STATIC_GUARD: value})

    async def set_eco_boost(self, option: str) -> bool:
        """Set Eco Boost ('off' / 'on').

        Returns False when DryCavity_ChangeStatusEcoBoost is not True or
        when the option key is unrecognised.
        """
        value = ECO_BOOST_SET_VALUES.get(option)
        if value is None or not self.get_eco_boost_changeable():
            return False
        return await self.send_attributes({ATTR_ECO_BOOST: value})

    async def set_manual_dry_time(self, seconds: int) -> bool:
        """Set manual dry time (fail-closed).

        The wire value is in seconds (DDM-proven: 1800 = 30 minutes).

        Validation is fail-closed: every code path that does NOT resolve to
        a confirmed Quick-group or Timed-Dry-group cycle with a valid duration
        for that group returns False without calling send_attributes().
        This prevents accidental sends when CycleSelect is missing, unknown,
        or a known non-MDT cycle — even when ChangeStatusManualDryTime is "1"
        (live evidence: gate observed "1" while cycle was TowelsHeavyDuty).

        Returns False when:
          - DryCavity_ChangeStatusManualDryTime is not True
          - CycleSelect is missing or unrecognised
          - current cycle is not in Quick-group or Timed-Dry-group
          - ``seconds`` is not in the set allowed for the current group
        """
        if not self.get_manual_dry_time_changeable():
            return False
        cycle_raw = self._get_attribute(ATTR_CYCLE)
        seconds_str = str(seconds)
        if cycle_raw in QUICK_GROUP_CYCLES:
            if seconds_str not in QUICK_MDT_ALLOWED_SECONDS:
                return False
            return await self.send_attributes({ATTR_MANUAL_DRY_TIME: seconds_str})
        if cycle_raw in TIMED_DRY_GROUP_CYCLES:
            if seconds_str not in TIMED_DRY_MDT_ALLOWED_SECONDS:
                return False
            return await self.send_attributes({ATTR_MANUAL_DRY_TIME: seconds_str})
        # Missing / unknown / non-MDT cycle — fail closed, no send.
        return False

    def get_remote_control_enabled(self) -> bool | None:
        """Return whether Remote Control is enabled on the appliance."""
        return self.attr_value_to_bool(self._get_attribute(ATTR_REMOTE_CONTROL_ENABLE))

    async def _send_operation(self, operation: str) -> bool:
        """Send a proven API144 laundry operation."""
        if not self.has_attribute(ATTR_REMOTE_CONTROL_ENABLE):
            return False
        return await self.send_attributes({ATTR_OPERATIONS: operation})

    async def start(self) -> bool:
        return await self._send_operation(OPERATION_START)

    async def pause(self) -> bool:
        return await self._send_operation(OPERATION_PAUSE)

    async def resume(self) -> bool:
        return await self._send_operation(OPERATION_RESUME)

    async def cancel(self) -> bool:
        return await self._send_operation(OPERATION_CANCEL)
