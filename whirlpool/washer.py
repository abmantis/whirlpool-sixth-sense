from abc import ABC, abstractmethod
from enum import Enum

from .appliance import Appliance


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


class Washer(Appliance, ABC):
    @abstractmethod
    def get_machine_state(self) -> MachineState | None:
        pass

    @abstractmethod
    def get_cycle_status_sensing(self) -> bool | None:
        pass

    @abstractmethod
    def get_cycle_status_filling(self) -> bool | None:
        pass

    @abstractmethod
    def get_cycle_status_soaking(self) -> bool | None:
        pass

    @abstractmethod
    def get_cycle_status_washing(self) -> bool | None:
        pass

    @abstractmethod
    def get_cycle_status_rinsing(self) -> bool | None:
        pass

    @abstractmethod
    def get_cycle_status_spinning(self) -> bool | None:
        pass

    @abstractmethod
    def get_dispense_1_level(self) -> int | None:
        pass

    def supports_dispense_level(self) -> bool:
        """Return whether ``get_dispense_1_level()`` is implemented.

        When this is ``False``, ``get_dispense_1_level()`` raises
        ``NotImplementedError``, so callers can skip the dispense level.
        """
        return True

    @abstractmethod
    def get_door_open(self) -> bool | None:
        pass

    @abstractmethod
    def get_time_remaining(self) -> int | None:
        pass

    def get_cycle_time_complete(self) -> int | None:
        """Return the Unix time (s) at which the running cycle is predicted to end.

        ``None`` when no cycle is running or the backend does not report it.
        Only the AWS IoT backend reports it; other backends return ``None``.
        """
        return None
