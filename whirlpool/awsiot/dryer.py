"""Concrete awsiot Dryer — translates the MQTT state to the Dryer ABC.

The AWS IoT state payload nests the laundry cavity under a `dryer` key and
uses camelCase/attribute-style values (see `tests/data/awsiot/dryer_state.json`
captured from a Maytag MGD7020RF0). Read-only accessors are grounded in that
fixture; setters and capability-gated "changeable" flags are deferred until
laundry capability profiles are available.
"""

from typing import override

from ..dryer import Cycle, Dryness, MachineState, Temperature, WrinkleShield
from ..dryer import Dryer as BaseDryer
from ..types import ApplianceInfo
from .appliance import Appliance
from .mqttclient import MqttClient

# `dryer.applianceState` -> dryer MachineState. Only "standby" is confirmed
# from a captured fixture (dryer at rest); the remaining values are inferred
# from the HTTP API backend's state vocabulary and need confirmation against a
# live running/complete capture.
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
    "exception": MachineState.Exceptions,
    "exceptions": MachineState.Exceptions,
    "powerFailure": MachineState.PowerFailure,
    "cancelled": MachineState.Cancelled,
}

_WRINKLE_SHIELD_MAP: dict[str, WrinkleShield] = {
    "off": WrinkleShield.Off,
    "on": WrinkleShield.On,
    "onWithSteam": WrinkleShield.OnWithSteam,
}

# `dryer.currentPhase` values used to derive the cycle status flags. Like the
# washer phase vocabulary these are inferred pending a running-cycle capture.
_PHASE_AIRFLOW = "airflow"
_PHASE_COOL_DOWN = "coolDown"
_PHASE_DAMP = "damp"
_PHASE_DRYING = "drying"
_PHASE_LIMITED_CYCLE = "limitedCycle"
_PHASE_SENSING = "sensing"
_PHASE_STATIC_REDUCE = "staticReduce"
_PHASE_STEAMING = "steaming"
_PHASE_WET = "wet"


class Dryer(BaseDryer, Appliance):
    def __init__(
        self,
        mqttclient: MqttClient,
        appliance_info: ApplianceInfo,
    ):
        super().__init__(mqttclient, appliance_info)

    def _get_current_phase(self) -> str | None:
        """Return the dryer's current phase string, or None when absent."""
        return self._get_path_str("dryer", "currentPhase")

    def _phase_is(self, phase: str) -> bool | None:
        current = self._get_current_phase()
        return None if current is None else current == phase

    @override
    def get_machine_state(self) -> MachineState | None:
        raw = self._get_path_str("dryer", "applianceState")
        return _MACHINE_STATE_MAP.get(raw) if raw is not None else None

    @override
    def get_door_open(self) -> bool | None:
        raw = self._get_path_str("dryer", "doorStatus")
        if raw == "open":
            return True
        if raw == "closed":
            return False
        return None

    @override
    def get_time_remaining(self) -> int | None:
        return self._get_path_int("dryer", "cycleTime", "time")

    @override
    def get_drum_light_on(self) -> bool | None:
        return self._get_path_bool("dryer", "drumLight")

    # ------------------------------------------------------------------
    # Capability-gated "changeable" flags.
    #
    # The HTTP API backend sourced these from `*_ChangeStatus*` state
    # attributes. Under AWS IoT the equivalent signal is the appliance's
    # capability profile (the microwave backend's "supports_X" pattern), which
    # isn't captured yet for laundry models. Return None (unknown) until the
    # profiles are available.
    # ------------------------------------------------------------------

    @override
    def get_extra_power_changeable(self) -> bool | None:
        return None

    @override
    def get_steam_changeable(self) -> bool | None:
        return None

    @override
    def get_cycle_changeable(self) -> int | None:
        return None

    @override
    def get_dryness_changeable(self) -> bool | None:
        return None

    @override
    def get_manual_dry_time_changeable(self) -> int | None:
        return None

    @override
    def get_static_guard_changeable(self) -> bool | None:
        return None

    @override
    def get_temperature_changeable(self) -> bool | None:
        return None

    @override
    def get_wrinkle_shield_changeable(self) -> bool | None:
        return None

    # ------------------------------------------------------------------
    # Current set values.
    #
    # `dryLevel`, `dryTemperature` and the named cycle use model-specific
    # vocabularies that aren't confirmed yet; they're best-effort decoded and
    # fall back to None for unrecognised values.
    # ------------------------------------------------------------------

    @override
    def get_dryness(self) -> Dryness | None:
        raw = self._get_path_str("dryer", "dryLevel")
        if raw is None:
            return None
        return {
            "moreDry": Dryness.More,
            "normalDry": Dryness.Normal,
            "lessDry": Dryness.Less,
            "dampDry": Dryness.Low,
        }.get(raw)

    @override
    def get_manual_dry_time(self) -> int | None:
        return None

    @override
    def get_cycle(self) -> Cycle | None:
        raw = self._get_path_str("dryer", "cycleName")
        if raw is None:
            return None
        return {
            "regular": Cycle.Regular,
            "heavyDuty": Cycle.HeavyDuty,
            "delicates": Cycle.Delicates,
            "wrinkleControl": Cycle.WrinkleControl,
            "bulkyItems": Cycle.BulkyItems,
            "quickDry": Cycle.QuickDry,
            "sanitize": Cycle.Sanitize,
            "timedDry": Cycle.TimedDry,
            "towels": Cycle.Towels,
            "whites": Cycle.Whites,
            "normal": Cycle.Normal,
        }.get(raw)

    @override
    def get_cycle_status_airflow_status(self) -> bool | None:
        return self._phase_is(_PHASE_AIRFLOW)

    @override
    def get_cycle_status_cool_down(self) -> bool | None:
        return self._phase_is(_PHASE_COOL_DOWN)

    @override
    def get_cycle_status_damp(self) -> bool | None:
        return self._phase_is(_PHASE_DAMP)

    @override
    def get_cycle_status_drying(self) -> bool | None:
        return self._phase_is(_PHASE_DRYING)

    @override
    def get_cycle_status_limited_cycle(self) -> bool | None:
        return self._phase_is(_PHASE_LIMITED_CYCLE)

    @override
    def get_cycle_status_sensing(self) -> bool | None:
        return self._phase_is(_PHASE_SENSING)

    @override
    def get_cycle_status_static_reduce(self) -> bool | None:
        return self._phase_is(_PHASE_STATIC_REDUCE)

    @override
    def get_cycle_status_steaming(self) -> bool | None:
        return self._phase_is(_PHASE_STEAMING)

    @override
    def get_cycle_status_wet(self) -> bool | None:
        return self._phase_is(_PHASE_WET)

    @override
    def get_cycle_count(self) -> int | None:
        return None

    @override
    def get_damp_notification_tone_volume(self) -> int | None:
        return None

    @override
    def get_alert_tone_volume(self) -> int | None:
        return None

    @override
    def get_temperature(self) -> Temperature | None:
        raw = self._get_path_str("dryer", "dryTemperature")
        if raw is None:
            return None
        return {
            "air": Temperature.Air,
            "cool": Temperature.Cool,
            "warm": Temperature.Warm,
            "warmHigh": Temperature.WarmHigh,
            "hot": Temperature.Hot,
        }.get(raw)

    @override
    def get_wrinkle_shield(self) -> WrinkleShield | None:
        raw = self._get_path_str("dryer", "wrinkleShield")
        return _WRINKLE_SHIELD_MAP.get(raw) if raw is not None else None
