from typing import override

from ..washer import MachineState
from ..washer import Washer as BaseWasher
from .appliance import Appliance


class Washer(BaseWasher, Appliance):
    @override
    def get_machine_state(self) -> MachineState | None:
        raise NotImplementedError()

    @override
    def get_cycle_status_sensing(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_cycle_status_filling(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_cycle_status_soaking(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_cycle_status_washing(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_cycle_status_rinsing(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_cycle_status_spinning(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_dispense_1_level(self) -> int | None:
        raise NotImplementedError()

    @override
    def get_door_open(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_time_remaining(self) -> int | None:
        raise NotImplementedError()
