from typing import override

from ..aircon import Aircon as BaseAircon
from ..aircon import FanSpeed, Mode
from .appliance import Appliance


class Aircon(BaseAircon, Appliance):
    @override
    def get_current_temp(self) -> float | None:
        raise NotImplementedError()

    @override
    def get_current_humidity(self) -> int | None:
        raise NotImplementedError()

    @override
    def get_power_on(self) -> bool | None:
        raise NotImplementedError()

    @override
    async def set_power_on(self, on: bool) -> bool:
        raise NotImplementedError()

    @override
    def get_temp(self) -> float | None:
        raise NotImplementedError()

    @override
    async def set_temp(self, temp: float) -> bool:
        raise NotImplementedError()

    @override
    def get_humidity(self) -> int | None:
        raise NotImplementedError()

    @override
    async def set_humidity(self, temp: int) -> bool:
        raise NotImplementedError()

    @override
    def get_mode(self) -> Mode | None:
        raise NotImplementedError()

    @override
    def get_sixthsense_mode(self) -> bool:
        raise NotImplementedError()

    @override
    async def set_mode(self, mode: Mode) -> bool:
        raise NotImplementedError()

    @override
    def get_fanspeed(self) -> FanSpeed | None:
        raise NotImplementedError()

    @override
    async def set_fanspeed(self, speed: FanSpeed) -> bool:
        raise NotImplementedError()

    @override
    def get_h_louver_swing(self) -> bool | None:
        raise NotImplementedError()

    @override
    async def set_h_louver_swing(self, swing: bool) -> bool:
        raise NotImplementedError()

    @override
    def get_turbo_mode(self) -> bool | None:
        raise NotImplementedError()

    @override
    async def set_turbo_mode(self, turbo: bool) -> bool:
        raise NotImplementedError()

    @override
    def get_eco_mode(self) -> bool | None:
        raise NotImplementedError()

    @override
    async def set_eco_mode(self, eco: bool) -> bool:
        raise NotImplementedError()

    @override
    def get_quiet_mode(self) -> bool | None:
        raise NotImplementedError()

    @override
    async def set_quiet_mode(self, quiet: bool) -> bool:
        raise NotImplementedError()

    @override
    def get_display_on(self) -> bool | None:
        raise NotImplementedError()

    @override
    async def set_display_on(self, on: bool) -> bool:
        raise NotImplementedError()
