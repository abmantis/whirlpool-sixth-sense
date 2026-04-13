from abc import ABC, abstractmethod
from enum import Enum

from .appliance import Appliance


class Cavity(Enum):
    Upper = 0
    Lower = 1


# todo: figure out/plug in the other enums
class CookMode(Enum):
    Standby = 0
    Bake = 2
    ConvectBake = 6
    Broil = 8
    ConvectBroil = 9
    ConvectRoast = 16
    KeepWarm = 24
    AirFry = 41


# todo: figure out/plug in the other enums
class CookOperation(Enum):
    Cancel = 1
    Start = 2
    Modify = 4
    Pause = 5


# todo: figure out/plug in the other enums
class CavityState(Enum):
    Standby = 0
    Preheating = 1
    Cooking = 2
    NotPresent = 4


# todo: figure out/plug in what state = 2 is
class KitchenTimerState(Enum):
    Standby = 0
    Running = 1
    Completed = 3


class KitchenTimerOperations(Enum):
    Cancel = 1
    Start = 2


class KitchenTimer(ABC):
    @abstractmethod
    def get_total_time(self) -> str | None:
        pass

    @abstractmethod
    def get_remaining_time(self) -> str | None:
        pass

    @abstractmethod
    def get_state(self) -> KitchenTimerState | None:
        pass

    @abstractmethod
    async def set_timer(
        self,
        timer_time: int,
        operation: KitchenTimerOperations = KitchenTimerOperations.Start,
    ) -> bool:
        pass

    @abstractmethod
    async def cancel_timer(self) -> bool:
        pass


class Oven(Appliance, ABC):
    @abstractmethod
    def get_meat_probe_status(self, cavity: Cavity = Cavity.Upper) -> bool | None:
        pass

    @abstractmethod
    def get_door_opened(self, cavity: Cavity = Cavity.Upper) -> bool | None:
        pass

    @abstractmethod
    def get_display_brightness_percent(self) -> int | None:
        pass

    @abstractmethod
    async def set_display_brightness_percent(self, pct: int) -> bool:
        pass

    @abstractmethod
    def get_cook_time(self, cavity: Cavity = Cavity.Upper) -> int | None:
        pass

    @abstractmethod
    def get_control_locked(self) -> bool | None:
        pass

    @abstractmethod
    async def set_control_locked(self, on: bool) -> bool:
        pass

    @abstractmethod
    def get_light(self, cavity: Cavity = Cavity.Upper) -> bool | None:
        pass

    @abstractmethod
    async def set_light(self, on: bool, cavity: Cavity = Cavity.Upper) -> bool:
        pass

    @abstractmethod
    def get_temp(self, cavity: Cavity = Cavity.Upper) -> float | None:
        pass

    @abstractmethod
    def get_target_temp(self, cavity: Cavity = Cavity.Upper) -> float | None:
        pass

    @abstractmethod
    def get_cavity_state(self, cavity: Cavity = Cavity.Upper) -> CavityState | None:
        pass

    @abstractmethod
    def get_oven_cavity_exists(self, cavity: Cavity) -> bool:
        pass

    @abstractmethod
    def get_kitchen_timer(self, timer_id: int = 1) -> KitchenTimer:
        pass

    @abstractmethod
    def get_cook_mode(self, cavity: Cavity = Cavity.Upper) -> CookMode | None:
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def stop_cook(self, cavity: Cavity = Cavity.Upper) -> bool:
        pass

    @abstractmethod
    def get_sabbath_mode(self) -> bool | None:
        pass

    @abstractmethod
    async def set_sabbath_mode(self, on: bool) -> bool:
        pass
