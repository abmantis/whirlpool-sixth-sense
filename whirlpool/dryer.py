from abc import ABC, abstractmethod
from enum import Enum

from .appliance import Appliance


class Cycle(Enum):
    # Legacy flat cycles — preserved for model compatibility.
    Regular = 1
    HeavyDuty = 2
    Denim = 3  # Other models; not in WED9620HBK2 DDM
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
    # Matrix (What+How) cycles — DDM-proven on WED9620HBK2 (values 17–40)
    ColorsHeavyDuty = 17
    ColorsQuick = 18
    ColorsSanitize = 19
    ColorsTimedDry = 20
    ColorsWrinkleControl = 21
    BulkyHeavyDuty = 22
    BulkyQuick = 23
    BulkySanitize = 24
    BulkyTimedDry = 25
    BulkyWrinkleControl = 26
    DelicatesHeavyDuty = 27
    DelicatesQuick = 28
    # DelicatesSanitize intentionally omitted — DDM-forbidden
    DelicatesTimedDry = 29
    DelicatesWrinkleControl = 30
    TowelsHeavyDuty = 31
    TowelsQuick = 32
    TowelsSanitize = 33
    TowelsTimedDry = 34
    TowelsWrinkleControl = 35
    WhitesHeavyDuty = 36
    WhitesQuick = 37
    WhitesSanitize = 38
    WhitesTimedDry = 39
    WhitesWrinkleControl = 40
    Normal = 41  # Other models; not in WED9620HBK2 DDM


class Dryness(Enum):
    Low = 0  # Other models; not in WED9620HBK2 DDM
    Less = 1
    Normal = 4
    More = 7
    High = 10  # DDM label "None" on WED9620HBK2; kept as High for compat


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


class Temperature(Enum):
    Air = 0
    CoolLow = 1  # DDM-proven on WED9620HBK2 (new)
    Cool = 2  # DDM-proven on WED9620HBK2 (CoolMid)
    Warm = 5  # DDM-proven on WED9620HBK2 (WarmMid)
    WarmHigh = 6  # Other models; not in WED9620HBK2 DDM
    Hot = 8  # DDM-proven on WED9620HBK2 (HotMid)


class WrinkleShield(Enum):
    Off = 0
    On = 1
    OnWithSteam = 2


class Dryer(Appliance, ABC):
    @abstractmethod
    def get_machine_state(self) -> MachineState | None:
        pass

    @abstractmethod
    def get_door_open(self) -> bool | None:
        pass

    @abstractmethod
    def get_time_remaining(self) -> int | None:
        pass

    @abstractmethod
    def get_drum_light_on(self) -> bool | None:
        pass

    @abstractmethod
    def get_extra_power_changeable(self) -> bool | None:
        pass

    @abstractmethod
    def get_steam_changeable(self) -> bool | None:
        pass

    @abstractmethod
    def get_cycle_changeable(self) -> int | None:
        pass

    @abstractmethod
    def get_dryness_changeable(self) -> bool | None:
        pass

    @abstractmethod
    def get_manual_dry_time_changeable(self) -> int | None:
        pass

    @abstractmethod
    def get_static_guard_changeable(self) -> bool | None:
        pass

    @abstractmethod
    def get_temperature_changeable(self) -> bool | None:
        pass

    @abstractmethod
    def get_wrinkle_shield_changeable(self) -> bool | None:
        pass

    @abstractmethod
    def get_dryness(self) -> Dryness | None:
        pass

    @abstractmethod
    def get_manual_dry_time(self) -> int | None:
        pass

    @abstractmethod
    def get_cycle(self) -> Cycle | None:
        pass

    @abstractmethod
    def get_cycle_status_airflow_status(self) -> bool | None:
        pass

    @abstractmethod
    def get_cycle_status_cool_down(self) -> bool | None:
        pass

    @abstractmethod
    def get_cycle_status_damp(self) -> bool | None:
        pass

    @abstractmethod
    def get_cycle_status_drying(self) -> bool | None:
        pass

    @abstractmethod
    def get_cycle_status_limited_cycle(self) -> bool | None:
        pass

    @abstractmethod
    def get_cycle_status_sensing(self) -> bool | None:
        pass

    @abstractmethod
    def get_cycle_status_static_reduce(self) -> bool | None:
        pass

    @abstractmethod
    def get_cycle_status_steaming(self) -> bool | None:
        pass

    @abstractmethod
    def get_cycle_status_wet(self) -> bool | None:
        pass

    @abstractmethod
    def get_cycle_count(self) -> int | None:
        pass

    @abstractmethod
    def get_damp_notification_tone_volume(self) -> int | None:
        pass

    @abstractmethod
    def get_alert_tone_volume(self) -> int | None:
        pass

    @abstractmethod
    def get_temperature(self) -> Temperature | None:
        pass

    @abstractmethod
    def get_wrinkle_shield(self) -> WrinkleShield | None:
        pass

    def get_remote_control_enabled(self) -> bool | None:
        """Return remote-control status when supported by this transport."""
        return None

    async def start(self) -> bool:
        """Start the current cycle when supported by this transport."""
        return False

    async def pause(self) -> bool:
        """Pause the current cycle when supported by this transport."""
        return False

    async def resume(self) -> bool:
        """Resume the current cycle when supported by this transport."""
        return False

    async def cancel(self) -> bool:
        """Cancel the current cycle when supported by this transport."""
        return False


    def get_dry_cycle_pair(self) -> tuple[str, str] | None:
        return None

    def get_utility_cycle(self) -> str | None:
        return None

    def get_dryness_str(self) -> str | None:
        return None

    def get_temperature_str(self) -> str | None:
        return None

    def get_wrinkle_shield_str(self) -> str | None:
        return None

    def get_static_guard_str(self) -> str | None:
        return None

    def get_eco_boost_str(self) -> str | None:
        return None

    def get_eco_boost_changeable(self) -> bool | None:
        return None

    def get_manual_dry_time_options_minutes(self) -> list[str] | None:
        return None

    async def set_wrinkle_shield(self, option: str) -> bool:
        return False

    async def set_dryness(self, option: str) -> bool:
        return False

    async def set_temperature(self, option: str) -> bool:
        return False

    async def set_dry_cycle_pair(self, what: str, how: str) -> bool:
        return False

    async def set_utility_cycle(self, utility: str) -> bool:
        return False

    async def set_static_guard(self, option: str) -> bool:
        return False

    async def set_eco_boost(self, option: str) -> bool:
        return False

    async def set_manual_dry_time(self, seconds: int) -> bool:
        return False
