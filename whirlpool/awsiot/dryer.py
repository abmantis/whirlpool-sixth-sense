from typing import override

from ..dryer import Cycle, Dryness, MachineState, Temperature, WrinkleShield
from ..dryer import Dryer as BaseDryer
from ..types import ApplianceInfo
from .appliance import Appliance
from .capabilities import CapabilityProfile
from .factory import register_appliance
from .matchers import thing_category
from .mqttclient import MqttClient


@register_appliance(matcher=thing_category("fabriccare"), priority=4)
class Dryer(BaseDryer, Appliance):
    def __init__(
        self,
        mqttclient: MqttClient,
        appliance_info: ApplianceInfo,
        capability_profile: CapabilityProfile,
    ):
        super().__init__(mqttclient, appliance_info, capability_profile)

    @override
    def get_machine_state(self) -> MachineState | None:
        raise NotImplementedError()

    @override
    def get_door_open(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_time_remaining(self) -> int | None:
        raise NotImplementedError()

    @override
    def get_drum_light_on(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_extra_power_changeable(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_steam_changeable(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_cycle_changeable(self) -> int | None:
        raise NotImplementedError()

    @override
    def get_dryness_changeable(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_manual_dry_time_changeable(self) -> int | None:
        raise NotImplementedError()

    @override
    def get_static_guard_changeable(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_temperature_changeable(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_wrinkle_shield_changeable(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_dryness(self) -> Dryness | None:
        raise NotImplementedError()

    @override
    def get_manual_dry_time(self) -> int | None:
        raise NotImplementedError()

    @override
    def get_cycle(self) -> Cycle | None:
        raise NotImplementedError()

    @override
    def get_cycle_status_airflow_status(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_cycle_status_cool_down(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_cycle_status_damp(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_cycle_status_drying(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_cycle_status_limited_cycle(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_cycle_status_sensing(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_cycle_status_static_reduce(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_cycle_status_steaming(self) -> bool | None:
        raise NotImplementedError()

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
        raise NotImplementedError()

    @override
    def get_wrinkle_shield(self) -> WrinkleShield | None:
        raise NotImplementedError()
