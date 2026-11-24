from typing import override

from ..dishwasher import Dishwasher as BaseDishwasher
from ..washer import MachineState
from .appliance import Appliance

ATTR_MACHINE_STATE = "Cavity_OperationStatusMachineState"
ATTR_DOOR_OPEN = "Cavity_OperationStatusDoorOpen"
ATTR_TIME_REMAINING = "Cavity_TimeStatusEstTimeRemaining"

MACHINE_STATE_MAP = {
    "1": MachineState.Standby,
    "3": MachineState.RunningMainCycle,
}


class Dishwasher(BaseDishwasher, Appliance):
    """HTTP API support based on idle and running JennAir JDTSS246GS0 samples."""

    @override
    def get_machine_state(self) -> MachineState | None:
        if (state_raw := self._get_attribute(ATTR_MACHINE_STATE)) is None:
            return None
        return MACHINE_STATE_MAP.get(state_raw)

    @override
    def get_door_open(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(ATTR_DOOR_OPEN))

    @override
    def get_time_remaining(self) -> int | None:
        return self._get_int_attribute(ATTR_TIME_REMAINING)
