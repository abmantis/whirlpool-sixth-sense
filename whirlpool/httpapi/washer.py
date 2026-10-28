import logging
from dataclasses import dataclass, field

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
ATTR_DISPENSE_1_ENABLE = "WashCavity_CycleSetBulkDispense1Enable"
ATTR_DISPENSE_2_ENABLE = "WashCavity_CycleSetBulkDispense2Enable"
ATTR_DISPENSE_1_CONCENTRATION = "WashCavity_OpSetBulkDispense1Concentration"
ATTR_DISPENSE_2_CONCENTRATION = "WashCavity_OpSetBulkDispense2Concentration"
ATTR_DISPENSE_2_SELECTION = "WashCavity_OpSetBulkDispense2Selection"
ATTR_CYCLE_SELECT = "WashCavity_CycleSetCycleSelect"
ATTR_FRESHENING_SELECT = "WashCavity_CycleSetFresheningSelect"
ATTR_CHANGE_STATUS_FRESHENING = "WashCavity_ChangeStatusFreshening"
ATTR_STEAM_ENABLE = "Cavity_CycleSetSteamEnable"
ATTR_STEAM_CHANGEABLE = "Cavity_ChangeStatusSteamChangeable"
ATTR_DOOR_OPEN = "Cavity_OpStatusDoorOpen"
ATTR_REMOTE_CONTROL_ENABLE = "XCat_RemoteSetRemoteControlEnable"
ATTR_OPERATIONS = "Cavity_OpSetOperations"

OPERATION_CANCEL = "1"
OPERATION_START = "2"
OPERATION_PAUSE = "5"
OPERATION_RESUME = "6"

# Per-cycle wash option attributes. Every wire name below is confirmed present
# in a WFW9620HBK3 DDM capture and defined in that model's
# dataModel.attributes.
ATTR_TEMPERATURE = "WashCavity_CycleSetTemperature"
ATTR_SPIN_SPEED = "WashCavity_CycleSetSpinSpeed"
ATTR_SOIL_LEVEL = "WashCavity_CycleSetSoilLevel"
ATTR_EXTRA_RINSE = "WashCavity_CycleSetExtraRinseSelect"
ATTR_PRESOAK = "WashCavity_CycleSetPresoakTimed"

# Appliance-reported changeability flags for the attributes above. Note the
# ExtraRinse flag is NOT named after its CycleSet attribute: the wire key is
# WashCavity_ChangeStatusExtraRinse, not ...ExtraRinseSelect (live-confirmed).
ATTR_CHANGE_STATUS_CYCLE_SELECT = "WashCavity_ChangeStatusCycleSelect"
ATTR_CHANGE_STATUS_TEMPERATURE = "WashCavity_ChangeStatusTemperature"
ATTR_CHANGE_STATUS_SPIN_SPEED = "WashCavity_ChangeStatusSpinSpeed"
ATTR_CHANGE_STATUS_SOIL_LEVEL = "WashCavity_ChangeStatusSoilLevel"
ATTR_CHANGE_STATUS_EXTRA_RINSE = "WashCavity_ChangeStatusExtraRinse"
ATTR_CHANGE_STATUS_PRESOAK = "WashCavity_ChangeStatusPresoakTimed"

# Fan Fresh is proven only for this exact model. Keep the gate here, next to
# the model-specific cycle matrix, so generic Washer instances cannot expose
# a setting merely because a similarly named attribute happens to be present.
FAN_FRESH_SUPPORTED_MODEL = "WFW9620HBK3"
FRESHENING_VALUES = {"off": 0, "on": 1}
FRESHENING_REVERSE = {value: key for key, value in FRESHENING_VALUES.items()}

# Steam Enable is DDM-proven for the same exact model (WFW9620HBK3 capture:
# Cavity_CycleSetSteamEnable="0", Cavity_ChangeStatusSteamChangeable="1").
STEAM_SUPPORTED_MODEL = "WFW9620HBK3"
STEAM_ENABLE_VALUES = {"off": 0, "on": 1}
STEAM_ENABLE_REVERSE = {value: key for key, value in STEAM_ENABLE_VALUES.items()}

# Download & Go Specialty cycles are DDM-proven for WFW9620HBK3.
SPECIALTY_SUPPORTED_MODEL = "WFW9620HBK3"
ATTR_DOWNLOAD_AND_GO = "Cavity_CycleSetDownloadAndGo"
ATTR_SPECIALTY_CYCLE_ID = "Cavity_CycleSetSpecialtyCycleId"
ATTR_CYCLE_NAME = "Cavity_CycleSetCycleName"


@dataclass(frozen=True)
class SpecialtyPreset:
    """Fixed wire values for one Download & Go preset."""

    cycle_name: str
    cycle_select: int
    temperature: int
    spin_speed: int
    soil_level: int


SPECIALTY_PRESETS: dict[str, SpecialtyPreset] = {
    "coats_jackets": SpecialtyPreset("Jackets", 70, 0, 4, 2),
    "diapers": SpecialtyPreset("Diapers", 92, 4, 5, 2),
    "sleeping_bags": SpecialtyPreset("SleepingBags", 22, 2, 3, 2),
    "comforters": SpecialtyPreset("Comforters", 90, 2, 3, 0),
    "machine_wash_curtains": SpecialtyPreset("Curtains", 44, 0, 3, 0),
    "swimwear": SpecialtyPreset("Swimwear", 65, 0, 3, 0),
    "activewear": SpecialtyPreset("Activewear", 1, 2, 5, 2),
    "jeans": SpecialtyPreset("Jeans", 11, 2, 5, 1),
    "blankets": SpecialtyPreset("Blankets", 50, 3, 5, 1),
    "lingerie": SpecialtyPreset("Lingerie", 70, 1, 2, 0),
    "business_casual": SpecialtyPreset("BusinessCasual", 16, 1, 4, 1),
}
SPECIALTY_OPTION_BY_CYCLE_NAME = {
    preset.cycle_name: option for option, preset in SPECIALTY_PRESETS.items()
}

# DDM-proven combined What-to-Wash / How-to-Wash values for WFW9620HBK3.
WASH_CYCLE_MATRIX = {
    ("regular", "normal"): 1,
    ("regular", "quick"): 4,
    ("regular", "wrinkle_control"): 16,
    ("regular", "heavy_duty"): 2,
    ("regular", "cold_wash"): 18,
    ("regular", "sanitize"): 3,
    ("colors", "normal"): 24,
    ("colors", "quick"): 47,
    ("colors", "wrinkle_control"): 49,
    ("colors", "heavy_duty"): 46,
    ("colors", "cold_wash"): 44,
    ("colors", "sanitize"): 48,
    ("whites", "normal"): 10,
    ("whites", "quick"): 91,
    ("whites", "wrinkle_control"): 93,
    ("whites", "heavy_duty"): 90,
    ("whites", "cold_wash"): 88,
    ("whites", "sanitize"): 92,
    ("towels", "normal"): 11,
    ("towels", "quick"): 85,
    ("towels", "wrinkle_control"): 87,
    ("towels", "heavy_duty"): 84,
    ("towels", "cold_wash"): 82,
    ("towels", "sanitize"): 86,
    ("delicates", "normal"): 5,
    ("delicates", "quick"): 68,
    ("delicates", "wrinkle_control"): 70,
    ("delicates", "heavy_duty"): 67,
    ("delicates", "cold_wash"): 65,
    ("delicates", "sanitize"): 69,
    ("bulky", "normal"): 22,
    ("bulky", "quick"): 53,
    ("bulky", "wrinkle_control"): 54,
    ("bulky", "heavy_duty"): 52,
    ("bulky", "cold_wash"): 50,
}
WASH_CYCLE_REVERSE = {value: key for key, value in WASH_CYCLE_MATRIX.items()}

# ---------------------------------------------------------------------------
# Utility cycles
# ---------------------------------------------------------------------------
# Standalone cycle modes that live outside the What+How matrix but are written
# to the SAME wire attribute (WashCavity_CycleSetCycleSelect). Both values are
# DDM-proven on WFW9620HBK3 and are exposed by the official app through the
# separate SetUtilityCycle capability object rather than SetCycle:
#   Capability.WashCavity.SetUtilityCycle = {
#       WashCavity_CycleSetCycleSelectWashCycleDrainSpin,
#       WashCavity_CycleSetCycleSelectWashCycleCleanWasher }
# Semantically separate from normal cycles: get_wash_cycle_pair() returns None
# while one of these is selected, and get_utility_cycle() returns the key.
ATTRVAL_CYCLE_DRAIN_SPIN = 8
ATTRVAL_CYCLE_CLEAN_WASHER = 20

UTILITY_CYCLE_VALUES: dict[str, int] = {
    "drain_spin": ATTRVAL_CYCLE_DRAIN_SPIN,
    "clean_washer": ATTRVAL_CYCLE_CLEAN_WASHER,
}
UTILITY_CYCLE_REVERSE: dict[int, str] = {
    value: key for key, value in UTILITY_CYCLE_VALUES.items()
}

# ---------------------------------------------------------------------------
# Per-cycle wash option enums
# ---------------------------------------------------------------------------
# Wire values come from the WFW9620HBK3 DDM dataModel.attributes EnumValues
# blocks. Insertion order is the natural display order for UI option lists.
#
# SpinSpeed has NO wire value 1 - the DDM enum is {0,2,3,4,5}. A caller that
# tries to send 1 is rejected because there is no option key that maps to it.
WASH_TEMPERATURE_VALUES: dict[str, int] = {
    "cold": 0,
    "cool": 1,
    "warm": 2,
    "hot": 3,
    "extra_hot": 4,
}
WASH_TEMPERATURE_REVERSE = {v: k for k, v in WASH_TEMPERATURE_VALUES.items()}

WASH_SPIN_SPEED_VALUES: dict[str, int] = {
    "off": 0,
    "low": 2,
    "medium": 3,
    "high": 4,
    "extra_high": 5,
}
WASH_SPIN_SPEED_REVERSE = {v: k for k, v in WASH_SPIN_SPEED_VALUES.items()}

WASH_SOIL_LEVEL_VALUES: dict[str, int] = {
    "light": 0,
    "normal": 1,
    "heavy": 2,
}
WASH_SOIL_LEVEL_REVERSE = {v: k for k, v in WASH_SOIL_LEVEL_VALUES.items()}

WASH_EXTRA_RINSE_VALUES: dict[str, int] = {"off": 0, "on": 1}
WASH_EXTRA_RINSE_REVERSE = {v: k for k, v in WASH_EXTRA_RINSE_VALUES.items()}

# Presoak is a DDM "List" attribute, not a range: only these four wire values
# (seconds) appear in any per-cycle Required block. Anything else is rejected.
WASH_PRESOAK_VALUES: dict[str, int] = {
    "off": 0,
    "30_min": 1800,
    "1_hour": 3600,
    "8_hour": 28800,
}
WASH_PRESOAK_REVERSE = {v: k for k, v in WASH_PRESOAK_VALUES.items()}

# ---------------------------------------------------------------------------
# Per-cycle capability table
# ---------------------------------------------------------------------------
# Machine-extracted from the WFW9620HBK3 DDM response at
# personality.capability[0].Capability.WashCavity.CapabilityData - one entry per
# WashCavity_CycleSetCycleSelect enum value. An attribute that appears in a
# cycle's Required (or Optional) block is available for that cycle; an attribute
# absent from the entry entirely is NOT available for that cycle.
#
# Only three shapes occur across all 38 cycles, which is why the table below can
# share frozensets rather than repeating literals:
#   Temperature  {0,1,2,3,4} everywhere EXCEPT the five Sanitize cycles, which
#                are locked to {4} (ExtraHot).
#   SpinSpeed    {0,3,4,5} (no Low) for the five Regular-family cycles
#                1/2/3/4/18; {0,2,3,4,5} for every other cycle that has spin.
#   SoilLevel    {0,1,2} for every cycle that has soil at all.
#
# IMPORTANT (evidence note): the DDM restricts the temperature ENUMERATION only
# for Sanitize. For every other cycle it lists all five temperatures and varies
# only the Default. Per-cycle temperature *caps* (for example "Quick is capped
# at Warm", or "Cold Wash is Cold-only") are NOT present in this DDM response
# and are deliberately NOT enforced here - enforcing them would block values the
# appliance's own capability data declares legal.
_TEMPERATURES_ALL = frozenset({0, 1, 2, 3, 4})
_TEMPERATURES_SANITIZE = frozenset({4})
_SPIN_SPEEDS_ALL = frozenset({0, 2, 3, 4, 5})
_SPIN_SPEEDS_NO_LOW = frozenset({0, 3, 4, 5})
_SOIL_LEVELS_ALL = frozenset({0, 1, 2})
_NO_VALUES: frozenset[int] = frozenset()


@dataclass(frozen=True)
class CycleCapability:
    """Which options the DDM declares available for one cycle.

    An empty value set, or a False flag, means the option does not exist for
    that cycle at all and must not be written while it is selected.

    The default_* fields record the DDM-proven initialization value for each
    option (the value the official Whirlpool app writes when selecting this
    cycle). None means the attribute is absent from this cycle's DDM
    CapabilityData and must not be included in the initialization payload.
    All default values are LEVEL B (static DDM-proven); see phase5c_ddm_results.json.
    """

    temperatures: frozenset[int] = field(default=_NO_VALUES)
    spin_speeds: frozenset[int] = field(default=_NO_VALUES)
    soil_levels: frozenset[int] = field(default=_NO_VALUES)
    presoak: bool = False
    extra_rinse: bool = False
    fan_fresh: bool = False
    steam: bool = False
    delay_time: bool = False
    # DDM-proven initialization defaults. None = attribute absent for this cycle.
    default_temperature: int | None = None
    default_spin_speed: int | None = None
    default_soil_level: int | None = None
    default_presoak: int | None = None
    default_extra_rinse: int | None = None
    default_fan_fresh: int | None = None
    default_steam: int | None = None


def _wash_cycle_capability(
    temperatures: frozenset[int],
    spin_speeds: frozenset[int],
    *,
    presoak: bool = True,
    steam: bool = True,
    default_temperature: int | None = None,
    default_spin_speed: int | None = None,
    default_soil_level: int | None = None,
) -> CycleCapability:
    """Build a normal (non-utility) wash cycle capability entry.

    Every normal cycle in this DDM offers soil level, extra rinse, fan fresh
    and delay time, so only the parts that actually vary are parameters.

    The fixed-at-zero defaults (extra_rinse, fan_fresh, presoak when supported,
    steam when supported) are set automatically from the boolean capability flags,
    matching the DDM pattern: every cycle initializes these to 0 (off) when the
    attribute is present at all.
    """
    return CycleCapability(
        temperatures=temperatures,
        spin_speeds=spin_speeds,
        soil_levels=_SOIL_LEVELS_ALL,
        presoak=presoak,
        extra_rinse=True,
        fan_fresh=True,
        steam=steam,
        delay_time=True,
        default_temperature=default_temperature,
        default_spin_speed=default_spin_speed,
        default_soil_level=default_soil_level,
        default_presoak=0 if presoak else None,
        default_extra_rinse=0,
        default_fan_fresh=0,
        default_steam=0 if steam else None,
    )


CYCLE_CAPABILITIES: dict[int, CycleCapability] = {
    # WashCycleNone - nothing selected, no options apply. No initialization
    # defaults (no cycle to initialize).
    0: CycleCapability(),
    # Regular family: SpinSpeedLow absent from all five.
    # DDM defaults from the private model capability capture (LEVEL B).
    1: _wash_cycle_capability(
        _TEMPERATURES_ALL,
        _SPIN_SPEEDS_NO_LOW,
        default_temperature=2,
        default_spin_speed=5,
        default_soil_level=1,
    ),
    2: _wash_cycle_capability(
        _TEMPERATURES_ALL,
        _SPIN_SPEEDS_NO_LOW,
        default_temperature=3,
        default_spin_speed=5,
        default_soil_level=1,
    ),
    3: _wash_cycle_capability(
        _TEMPERATURES_SANITIZE,
        _SPIN_SPEEDS_NO_LOW,
        presoak=False,
        default_temperature=4,
        default_spin_speed=5,
        default_soil_level=0,
    ),
    4: _wash_cycle_capability(
        _TEMPERATURES_ALL,
        _SPIN_SPEEDS_NO_LOW,
        default_temperature=2,
        default_spin_speed=5,
        default_soil_level=0,
    ),
    18: _wash_cycle_capability(
        _TEMPERATURES_ALL,
        _SPIN_SPEEDS_NO_LOW,
        steam=False,
        default_temperature=0,
        default_spin_speed=5,
        default_soil_level=2,
    ),
    # Category base cycles.
    5: _wash_cycle_capability(
        _TEMPERATURES_ALL,
        _SPIN_SPEEDS_ALL,
        default_temperature=2,
        default_spin_speed=2,
        default_soil_level=1,
    ),
    10: _wash_cycle_capability(
        _TEMPERATURES_ALL,
        _SPIN_SPEEDS_ALL,
        default_temperature=2,
        default_spin_speed=4,
        default_soil_level=2,
    ),
    11: _wash_cycle_capability(
        _TEMPERATURES_ALL,
        _SPIN_SPEEDS_ALL,
        default_temperature=2,
        default_spin_speed=5,
        default_soil_level=2,
    ),
    16: _wash_cycle_capability(
        _TEMPERATURES_ALL,
        _SPIN_SPEEDS_ALL,
        default_temperature=0,
        default_spin_speed=2,
        default_soil_level=0,
    ),
    22: _wash_cycle_capability(
        _TEMPERATURES_ALL,
        _SPIN_SPEEDS_ALL,
        default_temperature=2,
        default_spin_speed=4,
        default_soil_level=1,
    ),
    24: _wash_cycle_capability(
        _TEMPERATURES_ALL,
        _SPIN_SPEEDS_ALL,
        default_temperature=2,
        default_spin_speed=4,
        default_soil_level=0,
    ),
    # Colors compound cycles.
    44: _wash_cycle_capability(
        _TEMPERATURES_ALL,
        _SPIN_SPEEDS_ALL,
        steam=False,
        default_temperature=0,
        default_spin_speed=4,
        default_soil_level=0,
    ),
    46: _wash_cycle_capability(
        _TEMPERATURES_ALL,
        _SPIN_SPEEDS_ALL,
        default_temperature=3,
        default_spin_speed=4,
        default_soil_level=0,
    ),
    47: _wash_cycle_capability(
        _TEMPERATURES_ALL,
        _SPIN_SPEEDS_ALL,
        default_temperature=2,
        default_spin_speed=4,
        default_soil_level=0,
    ),
    48: _wash_cycle_capability(
        _TEMPERATURES_SANITIZE,
        _SPIN_SPEEDS_ALL,
        presoak=False,
        default_temperature=4,
        default_spin_speed=5,
        default_soil_level=0,
    ),
    49: _wash_cycle_capability(
        _TEMPERATURES_ALL,
        _SPIN_SPEEDS_ALL,
        default_temperature=0,
        default_spin_speed=2,
        default_soil_level=0,
    ),
    # Bulky compound cycles (Bulky+Sanitize does not exist).
    50: _wash_cycle_capability(
        _TEMPERATURES_ALL,
        _SPIN_SPEEDS_ALL,
        steam=False,
        default_temperature=0,
        default_spin_speed=4,
        default_soil_level=1,
    ),
    52: _wash_cycle_capability(
        _TEMPERATURES_ALL,
        _SPIN_SPEEDS_ALL,
        default_temperature=3,
        default_spin_speed=4,
        default_soil_level=1,
    ),
    53: _wash_cycle_capability(
        _TEMPERATURES_ALL,
        _SPIN_SPEEDS_ALL,
        default_temperature=2,
        default_spin_speed=4,
        default_soil_level=0,
    ),
    54: _wash_cycle_capability(
        _TEMPERATURES_ALL,
        _SPIN_SPEEDS_ALL,
        default_temperature=0,
        default_spin_speed=2,
        default_soil_level=0,
    ),
    # Delicates compound cycles.
    65: _wash_cycle_capability(
        _TEMPERATURES_ALL,
        _SPIN_SPEEDS_ALL,
        steam=False,
        default_temperature=0,
        default_spin_speed=2,
        default_soil_level=1,
    ),
    67: _wash_cycle_capability(
        _TEMPERATURES_ALL,
        _SPIN_SPEEDS_ALL,
        default_temperature=3,
        default_spin_speed=2,
        default_soil_level=1,
    ),
    68: _wash_cycle_capability(
        _TEMPERATURES_ALL,
        _SPIN_SPEEDS_ALL,
        default_temperature=2,
        default_spin_speed=2,
        default_soil_level=0,
    ),
    69: _wash_cycle_capability(
        _TEMPERATURES_SANITIZE,
        _SPIN_SPEEDS_ALL,
        presoak=False,
        default_temperature=4,
        default_spin_speed=5,
        default_soil_level=0,
    ),
    70: _wash_cycle_capability(
        _TEMPERATURES_ALL,
        _SPIN_SPEEDS_ALL,
        default_temperature=0,
        default_spin_speed=2,
        default_soil_level=0,
    ),
    # Towels compound cycles.
    82: _wash_cycle_capability(
        _TEMPERATURES_ALL,
        _SPIN_SPEEDS_ALL,
        steam=False,
        default_temperature=0,
        default_spin_speed=5,
        default_soil_level=2,
    ),
    84: _wash_cycle_capability(
        _TEMPERATURES_ALL,
        _SPIN_SPEEDS_ALL,
        default_temperature=3,
        default_spin_speed=5,
        default_soil_level=2,
    ),
    85: _wash_cycle_capability(
        _TEMPERATURES_ALL,
        _SPIN_SPEEDS_ALL,
        default_temperature=2,
        default_spin_speed=5,
        default_soil_level=0,
    ),
    86: _wash_cycle_capability(
        _TEMPERATURES_SANITIZE,
        _SPIN_SPEEDS_ALL,
        presoak=False,
        default_temperature=4,
        default_spin_speed=5,
        default_soil_level=0,
    ),
    87: _wash_cycle_capability(
        _TEMPERATURES_ALL,
        _SPIN_SPEEDS_ALL,
        default_temperature=0,
        default_spin_speed=2,
        default_soil_level=0,
    ),
    # Whites compound cycles.
    88: _wash_cycle_capability(
        _TEMPERATURES_ALL,
        _SPIN_SPEEDS_ALL,
        steam=False,
        default_temperature=0,
        default_spin_speed=4,
        default_soil_level=2,
    ),
    90: _wash_cycle_capability(
        _TEMPERATURES_ALL,
        _SPIN_SPEEDS_ALL,
        default_temperature=3,
        default_spin_speed=4,
        default_soil_level=2,
    ),
    91: _wash_cycle_capability(
        _TEMPERATURES_ALL,
        _SPIN_SPEEDS_ALL,
        default_temperature=2,
        default_spin_speed=4,
        default_soil_level=0,
    ),
    92: _wash_cycle_capability(
        _TEMPERATURES_SANITIZE,
        _SPIN_SPEEDS_ALL,
        presoak=False,
        default_temperature=4,
        default_spin_speed=5,
        default_soil_level=0,
    ),
    93: _wash_cycle_capability(
        _TEMPERATURES_ALL,
        _SPIN_SPEEDS_ALL,
        default_temperature=0,
        default_spin_speed=2,
        default_soil_level=0,
    ),
    # Utility cycles. Drain & Spin keeps spin / extra rinse / fan fresh only.
    # DDM default: SpinSpeed=5(ExtraHigh), ExtraRinse=0, FresheningSelect=0.
    # Temperature, SoilLevel, Presoak and Steam are absent from this cycle's
    # CapabilityData entirely and must not be written.
    ATTRVAL_CYCLE_DRAIN_SPIN: CycleCapability(
        spin_speeds=_SPIN_SPEEDS_ALL,
        extra_rinse=True,
        fan_fresh=True,
        delay_time=True,
        default_spin_speed=5,
        default_extra_rinse=0,
        default_fan_fresh=0,
    ),
    # Clean Washer with affresh declares no per-cycle options at all beyond an
    # optional delay. Nothing else may be written while it is selected, and the
    # DDM rule engine additionally excludes it from the Modify command (W6).
    # No initialization defaults: no option attributes exist for this cycle.
    ATTRVAL_CYCLE_CLEAN_WASHER: CycleCapability(delay_time=True),
}

# The per-cycle capability table, the option enums above and the utility cycle
# values are all taken from one model's DDM. Other washer models in this
# library use different cycle numbering and different enum values (the bundled
# WTW8127LW1 test fixture, for example, reports Temperature=5, which is not
# even a legal value on WFW9620HBK3), so every control built on this table is
# model-gated exactly like Fan Fresh and Steam already are. Other models keep
# their existing behaviour untouched and simply do not expose these controls
# until their own DDM has been captured.
CYCLE_OPTIONS_SUPPORTED_MODEL = "WFW9620HBK3"

DISPENSER_ENABLE_VALUES = {
    "disabled": 0,
    "enabled": 1,
    "disabled_next_cycle": 2,
}
DISPENSER_ENABLE_REVERSE = {
    value: key for key, value in DISPENSER_ENABLE_VALUES.items()
}

DISPENSER_CONCENTRATION_VALUES = {
    "2x": 50,
    "3x": 33,
    "4x": 25,
    "5x": 20,
    "6x": 17,
    "8x": 13,
}
DISPENSER_CONCENTRATION_REVERSE = {
    value: key for key, value in DISPENSER_CONCENTRATION_VALUES.items()
}

DISPENSER_2_SELECTION_VALUES = {
    "detergent": 1,
    "softener": 2,
}
DISPENSER_2_SELECTION_REVERSE = {
    value: key for key, value in DISPENSER_2_SELECTION_VALUES.items()
}

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

    def get_dispense_2_level(self) -> int | None:
        return self._get_int_attribute(ATTR_DISPENSE_2_LEVEL)

    def get_door_open(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_DOOR_OPEN))

    def get_time_remaining(self) -> int | None:
        return self._get_int_attribute(ATTR_CYCLE_STATUS_TIME_REMAINING)

    def get_wash_cycle_pair(self) -> tuple[str, str] | None:
        raw = self._get_int_attribute(ATTR_CYCLE_SELECT)
        return None if raw is None else WASH_CYCLE_REVERSE.get(raw)

    # ------------------------------------------------------------------
    # Cycle identity and per-cycle capability
    # ------------------------------------------------------------------

    def get_cycle_select(self) -> int | None:
        """Return the raw WashCavity_CycleSetCycleSelect wire value."""
        return self._get_int_attribute(ATTR_CYCLE_SELECT)

    def is_cycle_options_model_supported(self) -> bool:
        """Return whether the per-cycle option table applies to this model."""
        return self.appliance_info.model_number == CYCLE_OPTIONS_SUPPORTED_MODEL

    def get_cycle_capability(self) -> CycleCapability | None:
        """Return the DDM capability entry for the currently selected cycle.

        Returns None when the model is not the one this table was captured
        from, when no data has been fetched yet, or when the appliance reports
        a cycle value that is not in the captured DDM enum. Callers treat None
        as "unknown", not as "nothing is allowed": an unknown cycle must not
        invent restrictions that there is no evidence for.
        """
        if not self.is_cycle_options_model_supported():
            return None
        raw = self.get_cycle_select()
        return None if raw is None else CYCLE_CAPABILITIES.get(raw)

    def get_utility_cycle(self) -> str | None:
        """Return the active utility cycle key, or None.

        None means either that no data has been fetched or that the selected
        cycle is a normal What+How cycle rather than a utility cycle.
        """
        raw = self.get_cycle_select()
        return None if raw is None else UTILITY_CYCLE_REVERSE.get(raw)

    def is_utility_cycle_active(self) -> bool:
        """Return whether a utility cycle (Drain & Spin / Clean Washer) is set."""
        return self.get_utility_cycle() is not None

    def _cycle_initialization_payload(self, wire: int) -> dict[str, str]:
        """Build the full attribute payload for switching to cycle ``wire``.

        Returns a dict containing CycleSelect plus every option attribute that
        has a DDM-proven default for this cycle. Attributes absent from the
        cycle's DDM CapabilityData (default_* field is None) are omitted, so
        the appliance never receives an attribute it did not declare.

        The design intent is destination-only initialization: every present
        default is written even when the current value is already the same,
        mirroring the official Whirlpool app's observed behavior (live capture
        confirms SpinSpeed was written unchanged during a 70→5 transition).

        Evidence basis: LEVEL B (DDM-proven). Live confirmation of the full
        seven-attribute payload is required before trusting this in production;
        see the open questions in WHIRLPOOL_WASHER_SPECIALTY_CYCLE_DESIGN.md §9.

        This method is intentionally private: callers use set_wash_cycle_pair()
        and set_utility_cycle(), which apply the necessary model/fetch guards.
        """
        payload: dict[str, str] = {ATTR_CYCLE_SELECT: str(wire)}
        cap = CYCLE_CAPABILITIES.get(wire)
        if cap is None:
            return payload
        if cap.default_temperature is not None:
            payload[ATTR_TEMPERATURE] = str(cap.default_temperature)
        if cap.default_spin_speed is not None:
            payload[ATTR_SPIN_SPEED] = str(cap.default_spin_speed)
        if cap.default_soil_level is not None:
            payload[ATTR_SOIL_LEVEL] = str(cap.default_soil_level)
        if cap.default_presoak is not None:
            payload[ATTR_PRESOAK] = str(cap.default_presoak)
        if cap.default_extra_rinse is not None:
            payload[ATTR_EXTRA_RINSE] = str(cap.default_extra_rinse)
        if cap.default_fan_fresh is not None:
            payload[ATTR_FRESHENING_SELECT] = str(cap.default_fan_fresh)
        if cap.default_steam is not None:
            payload[ATTR_STEAM_ENABLE] = str(cap.default_steam)
        return payload

    async def set_utility_cycle(self, utility: str) -> bool:
        """Select a utility cycle ('drain_spin' or 'clean_washer').

        Writes the same wire attribute as a normal cycle, which is what the
        appliance expects - the separation is semantic, not protocol-level.

        Sends one combined send_attributes() call carrying CycleSelect plus
        every option default for this utility cycle (from the DDM), initializing
        all applicable attributes atomically in a single request. This matches
        the official Whirlpool app's behavior (LEVEL A: live capture confirmed
        multi-attribute initialization for normal cycles; utility-cycle behavior
        is LEVEL B until live-captured).

        Raises ValueError for an unknown utility cycle key. Returns False when
        the model is not WFW9620HBK3, when no data has been fetched, or when
        the appliance reports the cycle as not currently changeable.
        """
        value = UTILITY_CYCLE_VALUES.get(utility)
        if value is None:
            raise ValueError(f"Unknown utility cycle: {utility!r}")
        if not self.is_cycle_options_model_supported():
            return False
        if not self.has_attribute(ATTR_CYCLE_SELECT):
            return False
        if self.cycle_select_changeable() is not True:
            return False
        return await self.send_attributes(self._cycle_initialization_payload(value))

    # ------------------------------------------------------------------
    # Appliance-reported changeability flags
    # ------------------------------------------------------------------

    def cycle_select_changeable(self) -> bool | None:
        """Return the appliance-reported cycle changeability flag."""
        return self.attr_value_to_bool(
            self._get_attribute(ATTR_CHANGE_STATUS_CYCLE_SELECT)
        )

    def temperature_changeable(self) -> bool | None:
        """Return the appliance-reported temperature changeability flag."""
        return self.attr_value_to_bool(
            self._get_attribute(ATTR_CHANGE_STATUS_TEMPERATURE)
        )

    def spin_speed_changeable(self) -> bool | None:
        """Return the appliance-reported spin speed changeability flag."""
        return self.attr_value_to_bool(
            self._get_attribute(ATTR_CHANGE_STATUS_SPIN_SPEED)
        )

    def soil_level_changeable(self) -> bool | None:
        """Return the appliance-reported soil level changeability flag."""
        return self.attr_value_to_bool(
            self._get_attribute(ATTR_CHANGE_STATUS_SOIL_LEVEL)
        )

    def extra_rinse_changeable(self) -> bool | None:
        """Return the appliance-reported extra rinse changeability flag."""
        return self.attr_value_to_bool(
            self._get_attribute(ATTR_CHANGE_STATUS_EXTRA_RINSE)
        )

    def presoak_changeable(self) -> bool | None:
        """Return the appliance-reported presoak changeability flag."""
        return self.attr_value_to_bool(self._get_attribute(ATTR_CHANGE_STATUS_PRESOAK))

    # ------------------------------------------------------------------
    # Model-level support for the per-cycle option controls
    # ------------------------------------------------------------------

    def _supports_option(self, attribute: str, change_attribute: str) -> bool:
        return (
            self.is_cycle_options_model_supported()
            and self.has_attribute(attribute)
            and self.has_attribute(change_attribute)
        )

    def supports_temperature(self) -> bool:
        """Return whether this appliance exposes the temperature control."""
        return self._supports_option(ATTR_TEMPERATURE, ATTR_CHANGE_STATUS_TEMPERATURE)

    def supports_spin_speed(self) -> bool:
        """Return whether this appliance exposes the spin speed control."""
        return self._supports_option(ATTR_SPIN_SPEED, ATTR_CHANGE_STATUS_SPIN_SPEED)

    def supports_soil_level(self) -> bool:
        """Return whether this appliance exposes the soil level control."""
        return self._supports_option(ATTR_SOIL_LEVEL, ATTR_CHANGE_STATUS_SOIL_LEVEL)

    def supports_extra_rinse(self) -> bool:
        """Return whether this appliance exposes the extra rinse control."""
        return self._supports_option(ATTR_EXTRA_RINSE, ATTR_CHANGE_STATUS_EXTRA_RINSE)

    def supports_presoak(self) -> bool:
        """Return whether this appliance exposes the presoak control."""
        return self._supports_option(ATTR_PRESOAK, ATTR_CHANGE_STATUS_PRESOAK)

    def supports_utility_cycles(self) -> bool:
        """Return whether this appliance exposes the utility cycle control."""
        return self._supports_option(ATTR_CYCLE_SELECT, ATTR_CHANGE_STATUS_CYCLE_SELECT)

    # ------------------------------------------------------------------
    # Per-cycle availability
    # ------------------------------------------------------------------
    # Each of these answers "does the CURRENTLY selected cycle offer this
    # option?". When the capability is unknown they answer True, so an
    # unrecognised cycle never makes a control falsely disappear.

    def _cycle_allows(self, name: str) -> bool:
        capability = self.get_cycle_capability()
        if capability is None:
            return True
        value = getattr(capability, name)
        return bool(value)

    def cycle_supports_temperature(self) -> bool:
        """Return whether the selected cycle offers a temperature setting."""
        return self._cycle_allows("temperatures")

    def cycle_supports_spin_speed(self) -> bool:
        """Return whether the selected cycle offers a spin speed setting."""
        return self._cycle_allows("spin_speeds")

    def cycle_supports_soil_level(self) -> bool:
        """Return whether the selected cycle offers a soil level setting."""
        return self._cycle_allows("soil_levels")

    def cycle_supports_extra_rinse(self) -> bool:
        """Return whether the selected cycle offers extra rinse."""
        return self._cycle_allows("extra_rinse")

    def cycle_supports_presoak(self) -> bool:
        """Return whether the selected cycle offers presoak."""
        return self._cycle_allows("presoak")

    def cycle_supports_fan_fresh(self) -> bool:
        """Return whether the selected cycle offers Fan Fresh."""
        return self._cycle_allows("fan_fresh")

    def cycle_supports_steam(self) -> bool:
        """Return whether the selected cycle offers Steam."""
        return self._cycle_allows("steam")

    def cycle_supports_delay_time(self) -> bool:
        """Return whether the selected cycle offers a start delay."""
        return self._cycle_allows("delay_time")

    # ------------------------------------------------------------------
    # Allowed option keys for the selected cycle
    # ------------------------------------------------------------------

    @staticmethod
    def _allowed_keys(
        values: dict[str, int], allowed: frozenset[int] | None
    ) -> list[str]:
        if allowed is None:
            return list(values)
        return [key for key, value in values.items() if value in allowed]

    def get_supported_temperatures(self) -> list[str]:
        """Return the temperature option keys legal for the selected cycle."""
        capability = self.get_cycle_capability()
        allowed = None if capability is None else capability.temperatures
        return self._allowed_keys(WASH_TEMPERATURE_VALUES, allowed)

    def get_supported_spin_speeds(self) -> list[str]:
        """Return the spin speed option keys legal for the selected cycle."""
        capability = self.get_cycle_capability()
        allowed = None if capability is None else capability.spin_speeds
        return self._allowed_keys(WASH_SPIN_SPEED_VALUES, allowed)

    def get_supported_soil_levels(self) -> list[str]:
        """Return the soil level option keys legal for the selected cycle."""
        capability = self.get_cycle_capability()
        allowed = None if capability is None else capability.soil_levels
        return self._allowed_keys(WASH_SOIL_LEVEL_VALUES, allowed)

    def get_supported_extra_rinse_options(self) -> list[str]:
        """Return the extra rinse option keys legal for the selected cycle."""
        return (
            []
            if not self.cycle_supports_extra_rinse()
            else list(WASH_EXTRA_RINSE_VALUES)
        )

    def get_supported_presoak_options(self) -> list[str]:
        """Return the presoak option keys legal for the selected cycle."""
        return [] if not self.cycle_supports_presoak() else list(WASH_PRESOAK_VALUES)

    # ------------------------------------------------------------------
    # Per-cycle option getters
    # ------------------------------------------------------------------

    def get_temperature(self) -> str | None:
        """Return the current wash temperature option key."""
        raw = self._get_int_attribute(ATTR_TEMPERATURE)
        return None if raw is None else WASH_TEMPERATURE_REVERSE.get(raw)

    def get_spin_speed(self) -> str | None:
        """Return the current spin speed option key."""
        raw = self._get_int_attribute(ATTR_SPIN_SPEED)
        return None if raw is None else WASH_SPIN_SPEED_REVERSE.get(raw)

    def get_soil_level(self) -> str | None:
        """Return the current soil level option key."""
        raw = self._get_int_attribute(ATTR_SOIL_LEVEL)
        return None if raw is None else WASH_SOIL_LEVEL_REVERSE.get(raw)

    def get_extra_rinse(self) -> str | None:
        """Return the current extra rinse option key."""
        raw = self._get_int_attribute(ATTR_EXTRA_RINSE)
        return None if raw is None else WASH_EXTRA_RINSE_REVERSE.get(raw)

    def get_presoak(self) -> str | None:
        """Return the current presoak option key."""
        raw = self._get_int_attribute(ATTR_PRESOAK)
        return None if raw is None else WASH_PRESOAK_REVERSE.get(raw)

    def get_presoak_seconds(self) -> int | None:
        """Return the raw presoak wire value in seconds."""
        return self._get_int_attribute(ATTR_PRESOAK)

    # ------------------------------------------------------------------
    # Per-cycle option setters
    # ------------------------------------------------------------------
    # The Whirlpool cloud API accepts and stores a value that is illegal for
    # the selected cycle; the appliance only rejects it later, at Start. That
    # makes this library the enforcement layer, so every setter below validates
    # BEFORE sending:
    #   * an option key that does not exist               -> ValueError
    #   * an option the selected cycle does not offer     -> ValueError
    #   * a legal option that this cycle does not allow   -> ValueError
    #   * model without a captured DDM, missing attribute,
    #     or appliance-reported "not changeable"          -> False, nothing sent

    async def _set_cycle_option(
        self,
        label: str,
        option: str,
        values: dict[str, int],
        attribute: str,
        supported: bool,
        cycle_supported: bool,
        allowed: frozenset[int] | None,
        changeable: bool | None,
    ) -> bool:
        if option not in values:
            raise ValueError(f"Unknown {label} option: {option!r}")
        if not supported:
            return False
        if not cycle_supported:
            raise ValueError(
                f"{label} is not available on the currently selected cycle"
            )
        value = values[option]
        if allowed is not None and value not in allowed:
            raise ValueError(
                f"{label} {option!r} is not valid for the currently selected cycle"
            )
        if changeable is not True:
            return False
        return await self.send_attributes({attribute: str(value)})

    async def set_temperature(self, option: str) -> bool:
        """Set the wash temperature (cold/cool/warm/hot/extra_hot)."""
        capability = self.get_cycle_capability()
        return await self._set_cycle_option(
            "temperature",
            option,
            WASH_TEMPERATURE_VALUES,
            ATTR_TEMPERATURE,
            self.supports_temperature(),
            self.cycle_supports_temperature(),
            None if capability is None else capability.temperatures,
            self.temperature_changeable(),
        )

    async def set_spin_speed(self, option: str) -> bool:
        """Set the spin speed (off/low/medium/high/extra_high)."""
        capability = self.get_cycle_capability()
        return await self._set_cycle_option(
            "spin speed",
            option,
            WASH_SPIN_SPEED_VALUES,
            ATTR_SPIN_SPEED,
            self.supports_spin_speed(),
            self.cycle_supports_spin_speed(),
            None if capability is None else capability.spin_speeds,
            self.spin_speed_changeable(),
        )

    async def set_soil_level(self, option: str) -> bool:
        """Set the soil level (light/normal/heavy)."""
        capability = self.get_cycle_capability()
        return await self._set_cycle_option(
            "soil level",
            option,
            WASH_SOIL_LEVEL_VALUES,
            ATTR_SOIL_LEVEL,
            self.supports_soil_level(),
            self.cycle_supports_soil_level(),
            None if capability is None else capability.soil_levels,
            self.soil_level_changeable(),
        )

    async def set_extra_rinse(self, option: str) -> bool:
        """Set extra rinse (off/on)."""
        return await self._set_cycle_option(
            "extra rinse",
            option,
            WASH_EXTRA_RINSE_VALUES,
            ATTR_EXTRA_RINSE,
            self.supports_extra_rinse(),
            self.cycle_supports_extra_rinse(),
            None,
            self.extra_rinse_changeable(),
        )

    async def set_presoak(self, option: str | int) -> bool:
        """Set the presoak timer.

        Accepts either an option key ('off', '30_min', '1_hour', '8_hour') or
        the raw wire value in seconds. The DDM declares presoak as a fixed
        four-value List, not a range, so any other number of seconds - 900,
        for example - is rejected rather than rounded or passed through.

        A raw value is normalised to its option key here, before the shared
        cycle-option helper is called, so that helper keeps a single, precise
        `option: str` parameter rather than having to accept the union and
        re-derive the key itself.

        bool is rejected explicitly. Python treats bool as a subclass of int,
        so without this guard set_presoak(False) would silently resolve to the
        0-second key ('off') through the reverse lookup, which is not a value
        this method is documented to accept.
        """
        key: str
        if isinstance(option, bool):
            raise ValueError(f"Unknown presoak option: {option!r}")
        if isinstance(option, int):
            resolved = WASH_PRESOAK_REVERSE.get(option)
            if resolved is None:
                raise ValueError(f"Unknown presoak option: {option!r}")
            key = resolved
        else:
            key = option
        return await self._set_cycle_option(
            "presoak",
            key,
            WASH_PRESOAK_VALUES,
            ATTR_PRESOAK,
            self.supports_presoak(),
            self.cycle_supports_presoak(),
            None,
            self.presoak_changeable(),
        )

    def is_fan_fresh_model_supported(self) -> bool:
        """Return whether this is the exact model proven to support Fan Fresh."""
        return self.appliance_info.model_number == FAN_FRESH_SUPPORTED_MODEL

    def supports_fan_fresh(self) -> bool:
        """Return whether this model currently exposes the required DDM fields."""
        return (
            self.is_fan_fresh_model_supported()
            and self.has_attribute(ATTR_FRESHENING_SELECT)
            and self.has_attribute(ATTR_CHANGE_STATUS_FRESHENING)
        )

    def get_fan_fresh(self) -> str | None:
        """Return the current Fan Fresh option."""
        raw = self._get_int_attribute(ATTR_FRESHENING_SELECT)
        return None if raw is None else FRESHENING_REVERSE.get(raw)

    def fan_fresh_changeable(self) -> bool | None:
        """Return the appliance-reported Fan Fresh changeability flag."""
        return self.attr_value_to_bool(
            self._get_attribute(ATTR_CHANGE_STATUS_FRESHENING)
        )

    async def set_fan_fresh(self, option: str) -> bool:
        """Set Fan Fresh using the exact WFW9620HBK3 DDM enum mapping.

        Raises ValueError when the selected cycle does not offer Fan Fresh at
        all - Clean Washer with affresh declares no Fan Fresh option in its
        DDM capability entry. Every normal cycle and Drain & Spin do offer it,
        so this does not change behaviour for any previously working cycle.
        """
        if not self.supports_fan_fresh():
            return False
        if not self.cycle_supports_fan_fresh():
            raise ValueError(
                "Fan Fresh is not available on the currently selected cycle"
            )
        return await self._set_enum_attribute(
            ATTR_FRESHENING_SELECT, FRESHENING_VALUES, option
        )

    def is_steam_model_supported(self) -> bool:
        """Return whether this is the exact model proven to support Steam Enable."""
        return self.appliance_info.model_number == STEAM_SUPPORTED_MODEL

    def supports_steam(self) -> bool:
        """Return whether this model currently exposes the required DDM fields."""
        return (
            self.is_steam_model_supported()
            and self.has_attribute(ATTR_STEAM_ENABLE)
            and self.has_attribute(ATTR_STEAM_CHANGEABLE)
        )

    def get_steam(self) -> str | None:
        """Return the current Steam Enable option."""
        raw = self._get_int_attribute(ATTR_STEAM_ENABLE)
        return None if raw is None else STEAM_ENABLE_REVERSE.get(raw)

    def steam_changeable(self) -> bool | None:
        """Return the appliance-reported Steam Enable changeability flag."""
        return self.attr_value_to_bool(self._get_attribute(ATTR_STEAM_CHANGEABLE))

    async def set_steam(self, option: str) -> bool:
        """Set Steam Enable using the exact WFW9620HBK3 DDM enum mapping.

        Raises ValueError when the selected cycle does not offer Steam. The
        DDM omits Cavity_CycleSetSteamEnable entirely from Cold Wash (18) and
        from every What+ColdWash variant (44/50/65/82/88), and from both
        utility cycles. All Sanitize variants DO offer Steam - that question
        was previously open and is answered by the CapabilityData blocks.
        """
        if not self.supports_steam():
            return False
        if not self.cycle_supports_steam():
            raise ValueError("Steam is not available on the currently selected cycle")
        return await self._set_enum_attribute(
            ATTR_STEAM_ENABLE, STEAM_ENABLE_VALUES, option
        )

    def get_supported_specialty_cycles(self) -> list[str]:
        """Return supported Download & Go option keys for this washer."""
        if self.appliance_info.model_number != SPECIALTY_SUPPORTED_MODEL:
            return []
        required = (
            ATTR_DOWNLOAD_AND_GO,
            ATTR_SPECIALTY_CYCLE_ID,
            ATTR_CYCLE_SELECT,
            ATTR_CYCLE_NAME,
        )
        if not all(self.has_attribute(attribute) for attribute in required):
            return []
        return list(SPECIALTY_PRESETS)

    def get_specialty_cycle(self) -> str | None:
        """Return the active Download & Go option, if one is selected."""
        if not self.get_supported_specialty_cycles():
            return None
        if self._get_attribute(ATTR_DOWNLOAD_AND_GO) != "1":
            return None
        cycle_name = self._get_attribute(ATTR_CYCLE_NAME)
        if cycle_name is None:
            return None
        return SPECIALTY_OPTION_BY_CYCLE_NAME.get(cycle_name)

    async def set_specialty_cycle(self, option: str) -> bool:
        """Select a Download & Go preset without starting the washer."""
        preset = SPECIALTY_PRESETS.get(option)
        if preset is None:
            raise ValueError(f"Unknown specialty cycle: {option!r}")
        if not self.get_supported_specialty_cycles():
            return False
        if self.cycle_select_changeable() is not True:
            return False
        payload = {
            ATTR_DOWNLOAD_AND_GO: "1",
            ATTR_SPECIALTY_CYCLE_ID: "1",
            ATTR_CYCLE_SELECT: str(preset.cycle_select),
            ATTR_SOIL_LEVEL: str(preset.soil_level),
            ATTR_SPIN_SPEED: str(preset.spin_speed),
            ATTR_TEMPERATURE: str(preset.temperature),
            ATTR_CYCLE_NAME: preset.cycle_name,
        }
        return await self.send_attributes(payload)

    async def set_wash_cycle_pair(self, what: str, how: str) -> bool:
        """Set the cycle by What+How pair.

        Sends one combined send_attributes() call carrying CycleSelect plus
        every option default for the destination cycle (from the DDM),
        initializing all applicable attributes atomically in a single request.
        This matches the official Whirlpool app's observed behavior (LEVEL A:
        live capture confirmed a seven-attribute payload for cycle transitions,
        with SpinSpeed written even when unchanged, confirming destination-only
        semantics rather than a diff against current state).

        Raises ValueError for the DDM-absent Bulky+Sanitize combination and
        for any other unknown pair, rather than silently coercing it to
        something the appliance would accept. Mirrors the equivalent guard in
        Dryer.set_dry_cycle_pair() for Delicates+Sanitize.

        Note that the five non-Regular categories have no separate "+Normal"
        wire value: their category base value IS the Normal selection
        (Colors=24 carries the DDM name "ColorNormal", Regular=1 carries
        "RegularNormal"). The matrix is deliberately not a full 6x6 grid.
        """
        if what == "bulky" and how == "sanitize":
            raise ValueError(
                "Bulky+Sanitize is not supported on this appliance "
                "(absent from the DDM and from the official Whirlpool app)"
            )
        value = WASH_CYCLE_MATRIX.get((what, how))
        if value is None:
            raise ValueError(f"Unknown wash cycle combination: {what!r}/{how!r}")
        if not self.has_attribute(ATTR_CYCLE_SELECT):
            return False
        return await self.send_attributes(self._cycle_initialization_payload(value))

    async def set_wash_cycle_recipe(
        self,
        what: str,
        how: str,
        *,
        temperature: str | None = None,
        spin_speed: str | None = None,
        soil_level: str | None = None,
        presoak: str | None = None,
        extra_rinse: str | None = None,
        fan_fresh: str | None = None,
        steam: str | None = None,
    ) -> bool:
        """Set a What+How cycle and optional overrides in one request.

        Build the destination cycle's normal DDM initialization payload first,
        then replace only requested option values supported by that destination
        cycle. This avoids validating overrides against stale current-cycle
        state while preserving the proven regular-cycle payload shape.
        """
        if what == "bulky" and how == "sanitize":
            raise ValueError(
                "Bulky+Sanitize is not supported on this appliance "
                "(absent from the DDM and from the official Whirlpool app)"
            )

        wire = WASH_CYCLE_MATRIX.get((what, how))
        if wire is None:
            raise ValueError(f"Unknown wash cycle combination: {what!r}/{how!r}")

        if not self.has_attribute(ATTR_CYCLE_SELECT):
            return False

        capability = CYCLE_CAPABILITIES.get(wire)
        if capability is None:
            raise ValueError(f"No capability data for wash cycle: {wire}")

        payload = self._cycle_initialization_payload(wire)

        if temperature is not None:
            if temperature not in WASH_TEMPERATURE_VALUES:
                raise ValueError(f"Unknown temperature option: {temperature!r}")
            value = WASH_TEMPERATURE_VALUES[temperature]
            if not capability.temperatures:
                raise ValueError(
                    "temperature is not available on the destination cycle"
                )
            if value not in capability.temperatures:
                raise ValueError(
                    f"temperature {temperature!r} is not valid for "
                    "the destination cycle"
                )
            payload[ATTR_TEMPERATURE] = str(value)

        if spin_speed is not None:
            if spin_speed not in WASH_SPIN_SPEED_VALUES:
                raise ValueError(f"Unknown spin speed option: {spin_speed!r}")
            value = WASH_SPIN_SPEED_VALUES[spin_speed]
            if not capability.spin_speeds:
                raise ValueError("spin speed is not available on the destination cycle")
            if value not in capability.spin_speeds:
                raise ValueError(
                    f"spin speed {spin_speed!r} is not valid for the destination cycle"
                )
            payload[ATTR_SPIN_SPEED] = str(value)

        if soil_level is not None:
            if soil_level not in WASH_SOIL_LEVEL_VALUES:
                raise ValueError(f"Unknown soil level option: {soil_level!r}")
            value = WASH_SOIL_LEVEL_VALUES[soil_level]
            if not capability.soil_levels:
                raise ValueError("soil level is not available on the destination cycle")
            if value not in capability.soil_levels:
                raise ValueError(
                    f"soil level {soil_level!r} is not valid for the destination cycle"
                )
            payload[ATTR_SOIL_LEVEL] = str(value)

        if presoak is not None:
            if presoak not in WASH_PRESOAK_VALUES:
                raise ValueError(f"Unknown presoak option: {presoak!r}")
            if not capability.presoak:
                raise ValueError("presoak is not available on the destination cycle")
            payload[ATTR_PRESOAK] = str(WASH_PRESOAK_VALUES[presoak])

        if extra_rinse is not None:
            if extra_rinse not in WASH_EXTRA_RINSE_VALUES:
                raise ValueError(f"Unknown extra rinse option: {extra_rinse!r}")
            if not capability.extra_rinse:
                raise ValueError(
                    "extra rinse is not available on the destination cycle"
                )
            payload[ATTR_EXTRA_RINSE] = str(WASH_EXTRA_RINSE_VALUES[extra_rinse])

        if fan_fresh is not None:
            if fan_fresh not in FRESHENING_VALUES:
                raise ValueError(f"Unknown Fan Fresh option: {fan_fresh!r}")
            if not capability.fan_fresh:
                raise ValueError("Fan Fresh is not available on the destination cycle")
            payload[ATTR_FRESHENING_SELECT] = str(FRESHENING_VALUES[fan_fresh])

        if steam is not None:
            if steam not in STEAM_ENABLE_VALUES:
                raise ValueError(f"Unknown Steam option: {steam!r}")
            if not capability.steam:
                raise ValueError("Steam is not available on the destination cycle")
            payload[ATTR_STEAM_ENABLE] = str(STEAM_ENABLE_VALUES[steam])

        return await self.send_attributes(payload)

    def get_dispense_1_enable(self) -> str | None:
        raw = self._get_int_attribute(ATTR_DISPENSE_1_ENABLE)
        return None if raw is None else DISPENSER_ENABLE_REVERSE.get(raw)

    async def set_dispense_1_enable(self, option: str) -> bool:
        return await self._set_enum_attribute(
            ATTR_DISPENSE_1_ENABLE, DISPENSER_ENABLE_VALUES, option
        )

    def get_dispense_2_enable(self) -> str | None:
        raw = self._get_int_attribute(ATTR_DISPENSE_2_ENABLE)
        return None if raw is None else DISPENSER_ENABLE_REVERSE.get(raw)

    async def set_dispense_2_enable(self, option: str) -> bool:
        return await self._set_enum_attribute(
            ATTR_DISPENSE_2_ENABLE, DISPENSER_ENABLE_VALUES, option
        )

    def get_dispense_1_concentration(self) -> str | None:
        raw = self._get_int_attribute(ATTR_DISPENSE_1_CONCENTRATION)
        return None if raw is None else DISPENSER_CONCENTRATION_REVERSE.get(raw)

    async def set_dispense_1_concentration(self, option: str) -> bool:
        return await self._set_enum_attribute(
            ATTR_DISPENSE_1_CONCENTRATION, DISPENSER_CONCENTRATION_VALUES, option
        )

    def get_dispense_2_concentration(self) -> str | None:
        raw = self._get_int_attribute(ATTR_DISPENSE_2_CONCENTRATION)
        return None if raw is None else DISPENSER_CONCENTRATION_REVERSE.get(raw)

    async def set_dispense_2_concentration(self, option: str) -> bool:
        return await self._set_enum_attribute(
            ATTR_DISPENSE_2_CONCENTRATION, DISPENSER_CONCENTRATION_VALUES, option
        )

    def get_dispense_2_selection(self) -> str | None:
        raw = self._get_int_attribute(ATTR_DISPENSE_2_SELECTION)
        return None if raw is None else DISPENSER_2_SELECTION_REVERSE.get(raw)

    async def set_dispense_2_selection(self, option: str) -> bool:
        return await self._set_enum_attribute(
            ATTR_DISPENSE_2_SELECTION, DISPENSER_2_SELECTION_VALUES, option
        )

    async def _set_enum_attribute(
        self, attribute: str, values: dict[str, int], option: str
    ) -> bool:
        value = values.get(option)
        if value is None or not self.has_attribute(attribute):
            return False
        return await self.send_attributes({attribute: str(value)})

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
