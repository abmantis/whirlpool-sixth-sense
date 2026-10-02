"""Concrete awsiot Dryer: translates the MQTT state to the Dryer ABC.

The AWS IoT state nests the dryer under a `dryer` key, with camelCase string
values. Every Dryer carries the capability profile of its own part, which is
what routed it here, and the "changeable" flags it answers are read from that
profile's per-cycle option lists. The accessors only read the state; there are
no setters yet.

A wire value is decoded only when an AWS dryer has reported it, or when it
spells the enum member's own word and a real capability file enumerates it.
Anything else reads as unknown (None) or, for a phase flag, False. A getter
with no such value behind it raises NotImplementedError.
"""

import time
from typing import override

from ..dryer import Cycle, Dryness, MachineState, Temperature, WrinkleShield
from ..dryer import Dryer as BaseDryer
from ..types import ApplianceInfo
from .appliance import Appliance
from .capabilities import LaundryCapabilityProfile
from .mqttclient import MqttClient

# `dryer.applianceState` -> dryer MachineState. Only values an AWS dryer has
# reported are mapped; anything else reads as None (unknown). "idle" and
# "completed" are cycleTime.state values, not appliance states.
_MACHINE_STATE_MAP: dict[str, MachineState] = {
    # MGD7205RR0: https://github.com/abmantis/whirlpool-sixth-sense/issues/117#issuecomment-4246673850
    "standby": MachineState.Standby,
    # MED7205RW0: https://github.com/home-assistant/core/issues/151547#issuecomment-5658124608
    "programming": MachineState.Setting,
    # MED7205RW0: https://github.com/home-assistant/core/issues/151547#issuecomment-5658124608
    "running": MachineState.RunningMainCycle,
    # MED7205RW0: https://github.com/home-assistant/core/issues/151547#issuecomment-5658124608
    "paused": MachineState.Pause,
    # MED7205RW0: https://github.com/home-assistant/core/issues/151547#issuecomment-5658124608
    "end": MachineState.Complete,
}

_WRINKLE_SHIELD_MAP: dict[str, WrinkleShield] = {
    "off": WrinkleShield.Off,
    "on": WrinkleShield.On,
    "onWithSteam": WrinkleShield.OnWithSteam,
}

# `dryer.cycleName` -> Cycle. The other wire names read as None: mixed,
# bedLinen and the like have no Cycle member, and heavyLarge1, whitesNormal and
# jeansDenim have not been reported and are not their member's word.
_CYCLE_MAP: dict[str, Cycle] = {
    # MGD7020RF0: https://github.com/abmantis/whirlpool-sixth-sense/issues/138
    "normal": Cycle.Normal,
    # YMED7205RF0, live capture 2026-10-02, dial on Normal. Its W11771436 file
    # lists no "normal" cycle. Other parts list ecoEnergy beside normal, as two
    # cycles, and there get_cycle reads it as None:
    # W11808996: https://github.com/abmantis/whirlpool-sixth-sense/issues/179
    # W11804872: https://github.com/abmantis/whirlpool-sixth-sense/pull/167#issuecomment-5616074371
    "ecoEnergy": Cycle.Normal,
    # W11771436 file: https://github.com/abmantis/whirlpool-sixth-sense/issues/117#issuecomment-4246673850
    "delicates": Cycle.Delicates,
    "towels": Cycle.Towels,
    "sanitize1": Cycle.Sanitize,
    # MED7205RW0: https://github.com/home-assistant/core/issues/151547#issuecomment-5658124608
    "bulky": Cycle.BulkyItems,
    # MGD7205RR0: https://github.com/pickerin/maytag_laundry_homeassistant/blob/5ea31accfd67ff21aaf8b132b6efd4bd2f913c30/TS_APPLIANCE_API.md#L252
    "steamRefresh": Cycle.SteamRefresh,
    # MGD7020RF0: https://github.com/abmantis/whirlpool-sixth-sense/pull/167#pullrequestreview-5179281894
    "quickDryCottons": Cycle.QuickDry,
    # MGD7020RF0 (same review) and MED7205RW0 (#151547 above)
    "timed40": Cycle.TimedDry,
}

# `dryer.dryTemperature` -> Temperature. low and extraLow, which W11771436 also
# enumerates, have not been reported and are not their member's word.
_TEMPERATURE_MAP: dict[str, Temperature] = {
    # MGD7020RF0: https://github.com/abmantis/whirlpool-sixth-sense/pull/167#discussion_r3989687537
    "high": Temperature.Hot,
    "medium": Temperature.Warm,
    # W11771436 file: https://github.com/abmantis/whirlpool-sixth-sense/issues/117#issuecomment-4246673850
    "airOnly": Temperature.Air,
}

# `dryer.currentPhase` -> cycle status flag. Sources:
# - live MED7205RW0 timed40 cycle (dry, then coolDown through end):
#   https://github.com/home-assistant/core/issues/151547#issuecomment-5658124608
# - live MGD7020RF0 cycle (dry, coolDown):
#   https://github.com/abmantis/whirlpool-sixth-sense/pull/167#discussion_r3989687514
# - live ecoEnergy cycle (sensing for 3 s, then dry): YMED7205RF0 capture,
#   2026-10-02
# - W11771436 (MGD7205RR0, MED7205RW0) file: https://github.com/abmantis/whirlpool-sixth-sense/issues/117#issuecomment-4246673850
# Left unmapped, so every flag reads False: petsCare, which that file lists
# beside sensing but no dryer has reported.
_PHASES_COOL_DOWN = ("coolDown",)  # live
_PHASES_DRYING = ("dry",)  # live
_PHASES_SENSING = ("sensing",)  # live; in W11771436
_PHASES_STATIC_REDUCE = ("staticReduce",)  # in W11771436
_PHASES_STEAMING = ("steaming",)  # in W11771436


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
        """Return the dryer's current phase string, or None when absent."""
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
        """Seconds until the running cycle's predicted end, never below 0.

        cycleTime.time is not a countdown: a MED7205RW0 timed40 cycle held it
        at 2400, the cycle's length, from start to end. Its end snapshot puts
        the finish 39 s past the predicted end:
        https://github.com/home-assistant/core/issues/151547#issuecomment-5658124608
        """
        time_complete = self.get_cycle_time_complete()
        if time_complete is None:
            return None
        return max(0, time_complete - int(time.time()))

    @override
    def get_cycle_time_complete(self) -> int | None:
        """cycleTime.timeComplete while a cycle runs; None otherwise.

        Outside a running cycle the field is no prediction: an idle MED7205RW0
        reported one from 2022.
        """
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
        """Selected timed-dry length in minutes (sent as a string)."""
        raw = self._get_path_str("dryer", "timedDry")
        if raw is None:
            return None
        try:
            return int(raw)
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
