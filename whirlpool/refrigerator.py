from abc import ABC, abstractmethod

from .appliance import Appliance


class Refrigerator(Appliance, ABC):
    @abstractmethod
    def get_offset_temp(self) -> int | None:
        pass

    @abstractmethod
    async def set_offset_temp(self, temp) -> bool:
        pass

    @abstractmethod
    def get_temp(self) -> int | None:
        pass

    @abstractmethod
    async def set_temp(self, temp: int) -> bool:
        pass

    @abstractmethod
    def get_turbo_mode(self) -> bool | None:
        pass

    @abstractmethod
    async def set_turbo_mode(self, turbo: bool) -> bool:
        pass

    @abstractmethod
    def get_display_lock(self) -> bool | None:
        pass

    @abstractmethod
    async def set_display_lock(self, display: bool) -> bool:
        pass
