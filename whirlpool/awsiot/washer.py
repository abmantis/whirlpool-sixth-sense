"""Concrete awsiot Washer — translates the MQTT state to the Washer ABC.

The AWS IoT state payload nests the laundry cavity under a `washer` key and
uses camelCase/attribute-style values (see `tests/data/awsiot/washer_state.json`
captured from a Maytag MFW7020RF0). The read-only accessors below decode that
state; setters are intentionally absent until laundry capability profiles are
available (the microwave backend is the reference for how that will work).
"""

from typing import override

from ..types import ApplianceInfo
from ..washer import MachineState
from ..washer import Washer as BaseWasher
from .appliance import Appliance
from .mqttclient import MqttClient

# `washer.applianceState` -> washer MachineState. "standby", "running" and
# "end" are confirmed from live captures (Maytag MFW7020RF0); the remaining
# values are inferred from the HTTP API backend's state vocabulary and still
# need confirmation against a live capture.
_MACHINE_STATE_MAP: dict[str, MachineState] = {
    "standby": MachineState.Standby,
    "idle": MachineState.Standby,
    "setting": MachineState.Setting,
    "delayCountdown": MachineState.DelayCountdownMode,
    "delayPaused": MachineState.DelayPause,
    "pause": MachineState.Pause,
    "paused": MachineState.Pause,
    "running": MachineState.RunningMainCycle,
    "postCycle": MachineState.RunningPostCycle,
    "complete": MachineState.Complete,
    "completed": MachineState.Complete,
    "end": MachineState.Complete,
    "exception": MachineState.Exceptions,
    "exceptions": MachineState.Exceptions,
    "powerFailure": MachineState.PowerFailure,
}

# `washer.currentPhase` values used to derive the cycle status flags. "wash"
# is confirmed from a live running-cycle capture (Maytag MFW7020RF0); the
# remaining spellings are inferred and still need confirmation.
_PHASE_SENSING = "sensing"
_PHASE_FILLING = "filling"
_PHASE_SOAKING = "soaking"
_PHASE_WASHING = "wash"
_PHASE_RINSING = "rinsing"
_PHASE_SPINNING = "spinning"


class Washer(BaseWasher, Appliance):
    def __init__(
        self,
        mqttclient: MqttClient,
        appliance_info: ApplianceInfo,
    ):
        super().__init__(mqttclient, appliance_info)

    def _get_current_phase(self) -> str | None:
        """Return the washer's current phase string, or None when absent."""
        return self._get_path_str("washer", "currentPhase")

    def _phase_is(self, phase: str) -> bool | None:
        current = self._get_current_phase()
        return None if current is None else current == phase

    @override
    def get_machine_state(self) -> MachineState | None:
        raw = self._get_path_str("washer", "applianceState")
        return _MACHINE_STATE_MAP.get(raw) if raw is not None else None

    @override
    def get_cycle_status_sensing(self) -> bool | None:
        return self._phase_is(_PHASE_SENSING)

    @override
    def get_cycle_status_filling(self) -> bool | None:
        return self._phase_is(_PHASE_FILLING)

    @override
    def get_cycle_status_soaking(self) -> bool | None:
        return self._phase_is(_PHASE_SOAKING)

    @override
    def get_cycle_status_washing(self) -> bool | None:
        return self._phase_is(_PHASE_WASHING)

    @override
    def get_cycle_status_rinsing(self) -> bool | None:
        return self._phase_is(_PHASE_RINSING)

    @override
    def get_cycle_status_spinning(self) -> bool | None:
        return self._phase_is(_PHASE_SPINNING)

    @override
    def get_dispense_1_level(self) -> int | None:
        # No captured washer fixture exposes a bulk-dispense level yet;
        # return None (unsupported/unknown) until a dispenser model is captured.
        return None

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
        return self._get_path_int("washer", "cycleTime", "time")

    @override
    def get_cycle_time_complete(self) -> int | None:
        return self._get_path_int("washer", "cycleTime", "timeComplete")
