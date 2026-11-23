from abc import ABC, abstractmethod

from .appliance import Appliance
from .washer import MachineState


class Dishwasher(Appliance, ABC):
    @abstractmethod
    def get_machine_state(self) -> MachineState | None:
        pass

    @abstractmethod
    def get_door_open(self) -> bool | None:
        pass

    @abstractmethod
    def get_time_remaining(self) -> int | None:
        pass
