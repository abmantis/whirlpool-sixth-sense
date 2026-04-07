from abc import ABC, abstractmethod
from enum import Enum

from .appliance import Appliance


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


class Dryness(Enum):
    Low = 0
    Less = 1
    Normal = 4
    More = 7
    High = 10


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
    Cool = 2
    Warm = 5
    WarmHigh = 6
    Hot = 8


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
