"""Concrete awsiot Washer: translates the MQTT state to the Washer ABC.

The AWS IoT state nests the washer under a `washer` key, with camelCase string
values. Every Washer carries the capability profile of its own part, which is
what routed it here. The accessors below only read the state; there are no
setters yet.

A wire value is decoded only when an AWS laundry appliance has reported it, or,
for a phase, when it spells the flag's own word ("fill", "filling") and a real
capability file enumerates it. Anything else reads as unknown (None) or, for a
phase flag, False. The dispense level has no such value behind it, so
supports_dispense_level() is False and get_dispense_1_level() raises
NotImplementedError.
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

# `washer.currentPhase` -> cycle status flag. Front-loads report sense and
# wash; a top-load reports sensing, filling and washing, as its W11771387 file
# enumerates. Sources:
# - live MFW7020RF0 quick wash (sense, addGarment, wash, rinse, extraRinse,
#   rinse, spin): https://github.com/abmantis/whirlpool-sixth-sense/pull/167#discussion_r3989687563
# - live top-load regularNormal wash (sensing, filling, preWash, filling,
#   preWash, filling, washing, spin, rinse, spin, rinse, spin, done): live
#   MTW7205RF1 capture, 2026-10-02
# - W11771387 (MTW7205RR0) file: https://github.com/abmantis/whirlpool-sixth-sense/issues/117#issuecomment-4246673850
# - W11812024 (MFW7020RF0) file, vendored as tests/data/awsiot/washer_capability.json:
#   https://github.com/abmantis/whirlpool-sixth-sense/pull/167#issuecomment-5616074371
# - live MTW7205RR0 rinse: https://github.com/pickerin/maytag_laundry_homeassistant/blob/5ea31accfd67ff21aaf8b132b6efd4bd2f913c30/TS_APPLIANCE_API.md#L212
# Left unmapped, so every flag reads False: addGarment, default and done (no
# flag); preSense and intermediateSpin, which files enumerate but no washer has
# reported; and preWash, which a top-load reported between fills but which
# could be a soak or a wash.
_PHASES_SENSING = ("sense", "sensing")  # both live
_PHASES_FILLING = ("fill", "filling")  # fill in W11812024; filling live
_PHASES_SOAKING: tuple[str, ...] = ()  # see get_cycle_status_soaking
_PHASES_WASHING = ("wash", "washing")  # both live
_PHASES_RINSING = ("rinse", "extraRinse")  # both live, extraRinse between rinses
_PHASES_SPINNING = ("spin",)  # live


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
        """Always False while a phase is reported; None when it is absent.

        No reported or enumerated phase is known to mean soaking: preWash,
        which a top-load reported between fills, could be a soak or a wash.
        This still answers instead of raising, because Home Assistant reads
        all six phase flags on every update while the washer runs.
        """
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
    def supports_dispense_level(self) -> bool:
        """Always False: no AWS washer is known to report a dispense level.

        Not read from the capability profile. Its features.dispenser.type
        ("singleDose") and the per-cycle dispenser option ("off",
        "softenerOnly") are not levels.
        """
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
        return self._get_path_int("washer", "cycleTime", "time")

    @override
    def get_cycle_time_complete(self) -> int | None:
        return self._get_path_int("washer", "cycleTime", "timeComplete")
