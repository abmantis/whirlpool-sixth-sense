from abc import ABC, abstractmethod
from enum import Enum

from .appliance import Appliance


class Mode(Enum):
    Cool = 1
    Heat = 2
    Fan = 3
    SixthSense = 4


class FanSpeed(Enum):
    Off = 0
    Auto = 1
    Low = 2
    Medium = 3
    High = 4


class Aircon(Appliance, ABC):
    @abstractmethod
    def get_current_temp(self) -> float | None:
        pass

    @abstractmethod
    def get_current_humidity(self) -> int | None:
        pass

    @abstractmethod
    def get_power_on(self) -> bool | None:
        pass

    @abstractmethod
    async def set_power_on(self, on: bool) -> bool:
        pass

    @abstractmethod
    def get_temp(self) -> float | None:
        pass

    @abstractmethod
    async def set_temp(self, temp: float) -> bool:
        pass

    @abstractmethod
    def get_humidity(self) -> int | None:
        pass

    @abstractmethod
    async def set_humidity(self, temp: int) -> bool:
        pass

    @abstractmethod
    def get_mode(self) -> Mode | None:
        pass

    @abstractmethod
    def get_sixthsense_mode(self) -> bool:
        pass

    @abstractmethod
    async def set_mode(self, mode: Mode) -> bool:
        pass

    @abstractmethod
    def get_fanspeed(self) -> FanSpeed | None:
        pass

    @abstractmethod
    async def set_fanspeed(self, speed: FanSpeed) -> bool:
        pass

    @abstractmethod
    def get_h_louver_swing(self) -> bool | None:
        pass

    @abstractmethod
    async def set_h_louver_swing(self, swing: bool) -> bool:
        pass

    @abstractmethod
    def get_turbo_mode(self) -> bool | None:
        pass

    @abstractmethod
    async def set_turbo_mode(self, turbo: bool) -> bool:
        pass

    @abstractmethod
    def get_eco_mode(self) -> bool | None:
        pass

    @abstractmethod
    async def set_eco_mode(self, eco: bool) -> bool:
        pass

    @abstractmethod
    def get_quiet_mode(self) -> bool | None:
        pass

    @abstractmethod
    async def set_quiet_mode(self, quiet: bool) -> bool:
        pass

    @abstractmethod
    def get_display_on(self) -> bool | None:
        pass

    @abstractmethod
    async def set_display_on(self, on: bool) -> bool:
        pass
