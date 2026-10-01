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

# `washer.applianceState` -> washer MachineState. Only values AWS laundry has
# reported are mapped; anything else reads as None (unknown). "idle" and
# "completed" are cycleTime.state values, not appliance states.
_MACHINE_STATE_MAP: dict[str, MachineState] = {
    # MTW7205RR0: https://github.com/abmantis/whirlpool-sixth-sense/issues/117#issuecomment-4246673850
    "standby": MachineState.Standby,
    # MFW7020RF0: https://github.com/abmantis/whirlpool-sixth-sense/pull/167#discussion_r3989687548
    "programming": MachineState.Setting,
    # MTW7205RR0: https://github.com/pickerin/maytag_laundry_homeassistant/blob/5ea31accfd67ff21aaf8b132b6efd4bd2f913c30/TS_APPLIANCE_API.md#L208
    "running": MachineState.RunningMainCycle,
    # MTW7205RF1, live capture 2026-10-02, paused mid-cycle. A MED7205RW0 dryer,
    # same schema: https://github.com/home-assistant/core/issues/151547#issuecomment-5658124608
    "paused": MachineState.Pause,
    # MFW7020RF0: https://github.com/abmantis/whirlpool-sixth-sense/pull/167#discussion_r3989687563
    "end": MachineState.Complete,
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
        capability_profile: LaundryCapabilityProfile,
    ):
        super().__init__(mqttclient, appliance_info)
        self._capability_profile = capability_profile

    @property
    def capability_profile(self) -> LaundryCapabilityProfile:
        return self._capability_profile

    def option_changeable(self, option: str) -> bool:
        """Whether `option` can be changed right now.

        Not part of the Washer ABC; exposed for parity with the Dryer and for
        callers gating their own setters.
        """
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
