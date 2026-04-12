from typing import override

from ..oven import (
    Cavity,
    CavityState,
    CookMode,
    CookOperation,
    KitchenTimer,
)
from ..oven import Oven as BaseOven
from ..types import ApplianceInfo
from .appliance import Appliance
from .capabilities import CapabilityProfile
from .factory import register_appliance
from .matchers import thing_category
from .mqttclient import MqttClient


@register_appliance(matcher=thing_category("cooking"), priority=5)
class Oven(BaseOven, Appliance):
    def __init__(
        self,
        mqttclient: MqttClient,
        appliance_info: ApplianceInfo,
        capability_profile: CapabilityProfile,
    ):
        super().__init__(mqttclient, appliance_info, capability_profile)

    @override
    def get_meat_probe_status(self, cavity: Cavity = Cavity.Upper) -> bool | None:
        raise NotImplementedError()

    @override
    def get_door_opened(self, cavity: Cavity = Cavity.Upper) -> bool | None:
        raise NotImplementedError()

    @override
    def get_display_brightness_percent(self) -> int | None:
        raise NotImplementedError()

    @override
    async def set_display_brightness_percent(self, pct: int) -> bool:
        raise NotImplementedError()

    @override
    def get_cook_time(self, cavity: Cavity = Cavity.Upper) -> int | None:
        raise NotImplementedError()

    @override
    def get_control_locked(self) -> bool | None:
        raise NotImplementedError()

    @override
    async def set_control_locked(self, on: bool) -> bool:
        raise NotImplementedError()

    @override
    def get_light(self, cavity: Cavity = Cavity.Upper) -> bool | None:
        raise NotImplementedError()

    @override
    async def set_light(self, on: bool, cavity: Cavity = Cavity.Upper) -> bool:
        raise NotImplementedError()

    @override
    def get_temp(self, cavity: Cavity = Cavity.Upper) -> float | None:
        raise NotImplementedError()

    @override
    def get_target_temp(self, cavity: Cavity = Cavity.Upper) -> float | None:
        raise NotImplementedError()

    @override
    def get_cavity_state(self, cavity: Cavity = Cavity.Upper) -> CavityState | None:
        raise NotImplementedError()

    @override
    def get_oven_cavity_exists(self, cavity: Cavity) -> bool:
        raise NotImplementedError()

    @override
    def get_kitchen_timer(self, timer_id: int = 1) -> KitchenTimer:
        raise NotImplementedError()

    @override
    def get_cook_mode(self, cavity: Cavity = Cavity.Upper) -> CookMode | None:
        raise NotImplementedError()

    @override
    async def set_cook(
        self,
        target_temp: float,
        mode: CookMode = CookMode.Bake,
        cavity: Cavity = Cavity.Upper,
        rapid_preheat: bool | None = None,
        meat_probe_target_temp: float | None = None,
        delay_cook: int | None = None,
        operation_type: CookOperation = CookOperation.Start,
    ) -> bool:
        raise NotImplementedError()

    @override
    async def stop_cook(self, cavity: Cavity = Cavity.Upper) -> bool:
        raise NotImplementedError()

    @override
    def get_sabbath_mode(self) -> bool | None:
        raise NotImplementedError()

    @override
    async def set_sabbath_mode(self, on: bool) -> bool:
        raise NotImplementedError()
