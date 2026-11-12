"""AWS IoT Dryer."""

import time
from typing import override

from ..dryer import Cycle, Dryness, MachineState, Temperature, WrinkleShield
from ..dryer import Dryer as BaseDryer
from ..types import ApplianceInfo
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

_WRINKLE_SHIELD_MAP: dict[str, WrinkleShield] = {
    "off": WrinkleShield.Off,
    "on": WrinkleShield.On,
    "onWithSteam": WrinkleShield.OnWithSteam,
}

# `dryer.cycleName` -> Cycle.
_CYCLE_MAP: dict[str, Cycle] = {
    "normal": Cycle.Normal,
    # The Normal position on parts that list no "normal" cycle; see get_cycle().
    "ecoEnergy": Cycle.Normal,
    "delicates": Cycle.Delicates,
    "towels": Cycle.Towels,
    "bulky": Cycle.BulkyItems,
    "steamRefresh": Cycle.SteamRefresh,
    "quickDryCottons": Cycle.QuickDry,
    "timed40": Cycle.TimedDry,
}

_TEMPERATURE_MAP: dict[str, Temperature] = {
    "high": Temperature.Hot,
    "airOnly": Temperature.Air,
}

# `dryer.currentPhase` values behind each cycle status flag.
_PHASES_COOL_DOWN = ("coolDown",)
_PHASES_DRYING = ("dry",)
_PHASES_SENSING = ("sensing",)
_PHASES_STATIC_REDUCE = ("staticReduce",)
_PHASES_STEAMING = ("steaming",)


class Dryer(BaseDryer, Appliance):
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

    def _option_changeable(self, option: str) -> bool:
        """Whether `option` can be changed right now."""
        return self._capability_profile.option_changeable(
            self._get_path_str("dryer", "cycleName"),
            option,
            self._get_current_phase() or None,
        )

    def _get_current_phase(self) -> str | None:
        return self._get_path_str("dryer", "currentPhase")

    def _phase_is(self, *phases: str) -> bool | None:
        current = self._get_current_phase()
        return None if current is None else current in phases

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
        """Seconds until the running cycle's predicted end, never below 0."""
        time_complete = self.get_cycle_time_complete()
        if time_complete is None:
            return None
        return max(0, time_complete - int(time.time()))

    @override
    def get_cycle_time_complete(self) -> int | None:
        """cycleTime.timeComplete while a cycle runs; None otherwise."""
        if self._get_path_str("dryer", "cycleTime", "state") != "running":
            return None
        return self._get_path_int("dryer", "cycleTime", "timeComplete")

    @override
    def get_drum_light_on(self) -> bool | None:
        return self._get_path_bool("dryer", "drumLight")

    @override
    def get_extra_power_changeable(self) -> bool | None:
        return self._option_changeable("extraPower")

    @override
    def get_steam_changeable(self) -> bool | None:
        return self._option_changeable("steam")

    @override
    def get_cycle_changeable(self) -> int | None:
        raise NotImplementedError()

    @override
    def get_dryness_changeable(self) -> bool | None:
        return self._option_changeable("dryLevel")

    @override
    def get_manual_dry_time_changeable(self) -> int | None:
        return self._option_changeable("timedDry")

    @override
    def get_static_guard_changeable(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_temperature_changeable(self) -> bool | None:
        return self._option_changeable("dryTemperature")

    @override
    def get_wrinkle_shield_changeable(self) -> bool | None:
        return self._option_changeable("wrinkleShield")

    @override
    def get_dryness(self) -> Dryness | None:
        raise NotImplementedError()

    @override
    def get_manual_dry_time(self) -> int | None:
        """Selected timed-dry length in seconds; timedDry is sent in minutes."""
        raw = self._get_path_str("dryer", "timedDry")
        if raw is None:
            return None
        try:
            return int(raw) * 60
        except ValueError:
            return None

    @override
    def get_cycle(self) -> Cycle | None:
        raw = self._get_path_str("dryer", "cycleName")
        if raw == "ecoEnergy" and "normal" in self._capability_profile.cycles:
            # A cycle of its own on this part, not the Normal position.
            return None
        return _CYCLE_MAP.get(raw) if raw is not None else None

    @override
    def get_cycle_status_airflow_status(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_cycle_status_cool_down(self) -> bool | None:
        return self._phase_is(*_PHASES_COOL_DOWN)

    @override
    def get_cycle_status_damp(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_cycle_status_drying(self) -> bool | None:
        return self._phase_is(*_PHASES_DRYING)

    @override
    def get_cycle_status_limited_cycle(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_cycle_status_sensing(self) -> bool | None:
        return self._phase_is(*_PHASES_SENSING)

    @override
    def get_cycle_status_static_reduce(self) -> bool | None:
        return self._phase_is(*_PHASES_STATIC_REDUCE)

    @override
    def get_cycle_status_steaming(self) -> bool | None:
        return self._phase_is(*_PHASES_STEAMING)

    @override
    def get_cycle_status_wet(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_cycle_count(self) -> int | None:
        raise NotImplementedError()

    @override
    def get_damp_notification_tone_volume(self) -> int | None:
        raise NotImplementedError()

    @override
    def get_alert_tone_volume(self) -> int | None:
        raise NotImplementedError()

    @override
    def get_temperature(self) -> Temperature | None:
        raw = self._get_path_str("dryer", "dryTemperature")
        return _TEMPERATURE_MAP.get(raw) if raw is not None else None

    @override
    def get_wrinkle_shield(self) -> WrinkleShield | None:
        raw = self._get_path_str("dryer", "wrinkleShield")
        return _WRINKLE_SHIELD_MAP.get(raw) if raw is not None else None
