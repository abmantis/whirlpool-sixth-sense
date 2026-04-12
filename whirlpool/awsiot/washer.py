from typing import override

from ..types import ApplianceInfo
from ..washer import MachineState
from ..washer import Washer as BaseWasher
from .appliance import Appliance
from .capabilities import CapabilityProfile
from .factory import register_appliance
from .matchers import thing_category
from .mqttclient import MqttClient


@register_appliance(matcher=thing_category("laundry"), priority=5)
class Washer(BaseWasher, Appliance):
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
    def get_cycle_status_sensing(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_cycle_status_filling(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_cycle_status_soaking(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_cycle_status_washing(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_cycle_status_rinsing(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_cycle_status_spinning(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_dispense_1_level(self) -> int | None:
        raise NotImplementedError()

    @override
    def get_door_open(self) -> bool | None:
        raise NotImplementedError()

    @override
    def get_time_remaining(self) -> int | None:
        raise NotImplementedError()
