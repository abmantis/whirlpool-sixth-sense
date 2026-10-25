"""AWS IoT Washer."""

import time
from typing import override

from ..types import ApplianceInfo
from ..washer import MachineState
from ..washer import Washer as BaseWasher
from .appliance import Appliance
from .capabilities import LaundryCapabilityProfile
from .mqttclient import MqttClient

_MACHINE_STATE_MAP: dict[str, MachineState] = {
    "standby": MachineState.Standby,
    "programming": MachineState.Setting,
    "running": MachineState.RunningMainCycle,
    "paused": MachineState.Pause,
    "end": MachineState.Complete,
}

# `washer.currentPhase` values behind each cycle status flag. Front-loads
# report the stem (sense, wash), top-loads the gerund (sensing, washing).
_PHASES_SENSING = ("sense", "sensing")
_PHASES_FILLING = ("fill", "filling")
_PHASES_WASHING = ("wash", "washing")
_PHASES_RINSING = ("rinse", "extraRinse")
_PHASES_SPINNING = ("spin",)


class Washer(BaseWasher, Appliance):
    def __init__(
        self,
        mqttclient: MqttClient,
        appliance_info: ApplianceInfo,
        capability_profile: LaundryCapabilityProfile,
    ):
        super().__init__(mqttclient, appliance_info)
        self._capability_profile = capability_profile

    @property
    def capability_profile(self) -> LaundryCapabilityProfile:
        return self._capability_profile

    def _phase_is(self, *phases: str) -> bool | None:
        current = self._get_path_str("washer", "currentPhase")
        return None if current is None else current in phases

    @override
    def get_machine_state(self) -> MachineState | None:
        raw = self._get_path_str("washer", "applianceState")
        return _MACHINE_STATE_MAP.get(raw) if raw is not None else None

    @override
    def get_cycle_status_sensing(self) -> bool | None:
        return self._phase_is(*_PHASES_SENSING)

    @override
    def get_cycle_status_filling(self) -> bool | None:
        return self._phase_is(*_PHASES_FILLING)

    @override
    def get_cycle_status_soaking(self) -> bool | None:
        """No reported phase is known to mean soaking."""
        return False

    @override
    def get_cycle_status_washing(self) -> bool | None:
        return self._phase_is(*_PHASES_WASHING)

    @override
    def get_cycle_status_rinsing(self) -> bool | None:
        return self._phase_is(*_PHASES_RINSING)

    @override
    def get_cycle_status_spinning(self) -> bool | None:
        return self._phase_is(*_PHASES_SPINNING)

    @override
    def supports_dispense_level(self) -> bool:
        return False

    @override
    def get_dispense_1_level(self) -> int | None:
        raise NotImplementedError()

    @override
    def get_door_open(self) -> bool | None:
        raw = self._get_path_str("washer", "doorStatus")
        if raw == "open":
            return True
        if raw == "closed":
            return False
        return None

    @override
    def get_time_remaining(self) -> int | None:
        """Seconds until the running cycle's predicted end, never below 0."""
        time_complete = self.get_cycle_time_complete()
        if time_complete is None:
            return None
        return max(0, time_complete - int(time.time()))

    @override
    def get_cycle_time_complete(self) -> int | None:
        """cycleTime.timeComplete while a cycle runs; None otherwise."""
        if self._get_path_str("washer", "cycleTime", "state") != "running":
            return None
        return self._get_path_int("washer", "cycleTime", "timeComplete")
