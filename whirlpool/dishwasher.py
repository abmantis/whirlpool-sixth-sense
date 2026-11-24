from abc import ABC, abstractmethod

from .appliance import Appliance
from .washer import MachineState


class Dishwasher(Appliance, ABC):
    """Base interface for dishwashers.

    Initial HTTP attribute mappings are observed in idle and running diagnostics
    from JennAir JDTSS246GS0. Other models may expose different attributes or
    state values.
    """

    @abstractmethod
    def get_machine_state(self) -> MachineState | None:
        pass

    @abstractmethod
    def get_door_open(self) -> bool | None:
        pass

    @abstractmethod
    def get_time_remaining(self) -> int | None:
        pass
