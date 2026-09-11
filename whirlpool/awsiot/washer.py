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
from .capabilities import LaundryCapabilityProfile
from .mqttclient import MqttClient

# `washer.applianceState` -> washer MachineState. "standby", "running" and
# "end" are confirmed from live captures (Maytag MFW7020RF0); the remaining
# values are inferred from the HTTP API backend's state vocabulary and still
# need confirmation against a live capture.
_MACHINE_STATE_MAP: dict[str, MachineState] = {
    "standby": MachineState.Standby,
    "idle": MachineState.Standby,
    "setting": MachineState.Setting,
    # Reported while a cycle is being selected at the console;
    # confirmed from a live capture (Maytag MFW7020RF0).
    "programming": MachineState.Setting,
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
# rest are the phase names enumerated by the MFW7020RF0 capability file's
# per-option "changeable" lists, and still want confirmation from a live
# cycle. Phases the file declares but the ABC has no flag for: addGarment,
# default, postCare.
_PHASES_SENSING = ("sense", "preSense")
_PHASES_FILLING = ("fill",)
_PHASES_SOAKING = ("preWash",)
_PHASES_WASHING = ("wash",)
_PHASES_RINSING = ("rinse", "extraRinse")
_PHASES_SPINNING = ("spin", "intermediateSpin")


class Washer(BaseWasher, Appliance):
    def __init__(
        self,
        mqttclient: MqttClient,
        appliance_info: ApplianceInfo,
        capability_profile: LaundryCapabilityProfile | None = None,
    ):
        super().__init__(mqttclient, appliance_info)
        self._capability_profile = capability_profile

    @property
    def capability_profile(self) -> LaundryCapabilityProfile | None:
        return self._capability_profile

    def option_changeable(self, option: str) -> bool | None:
        """Whether `option` can be changed right now.

        Not part of the Washer ABC; exposed for parity with the Dryer and for
        callers gating their own setters. None when no profile is available.
        """
        if self._capability_profile is None:
            return None
        return self._capability_profile.option_changeable(
            self._get_path_str("washer", "cycleName"),
            option,
            self._get_current_phase() or None,
        )

    def _get_current_phase(self) -> str | None:
        """Return the washer's current phase string, or None when absent."""
        return self._get_path_str("washer", "currentPhase")

    def _phase_is(self, *phases: str) -> bool | None:
        current = self._get_current_phase()
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
        return self._phase_is(*_PHASES_SOAKING)

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
