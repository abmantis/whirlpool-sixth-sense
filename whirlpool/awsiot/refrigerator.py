from typing import override

from ..refrigerator import Refrigerator as BaseRefrigerator
from ..types import ApplianceInfo
from .appliance import Appliance
from .mqttclient import MqttClient


class Refrigerator(BaseRefrigerator, Appliance):
    def __init__(
        self,
        mqttclient: MqttClient,
        appliance_info: ApplianceInfo,
    ):
        super().__init__(mqttclient, appliance_info)

    @override
    def get_offset_temp(self) -> int | None:
        raise NotImplementedError()

    @override
    async def set_offset_temp(self, temp) -> bool:
        raise NotImplementedError()

    @override
    def get_temp(self) -> int | None:
        raise NotImplementedError()

    @override
    async def set_temp(self, temp: int) -> bool:
        raise NotImplementedError()

    @override
    def get_turbo_mode(self) -> bool | None:
        raise NotImplementedError()

    @override
    async def set_turbo_mode(self, turbo: bool) -> bool:
        raise NotImplementedError()

    @override
    def get_display_lock(self) -> bool | None:
        raise NotImplementedError()

    @override
    async def set_display_lock(self, display: bool) -> bool:
        raise NotImplementedError()
