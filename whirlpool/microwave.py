"""Abstract Microwave appliance contract (transport-agnostic)."""

from abc import ABC, abstractmethod
from enum import Enum

from .appliance import Appliance


class MicrowaveCavityState(Enum):
    Idle = "idle"
    Cooking = "cooking"
    Paused = "paused"
    Completed = "completed"
    TurningOff = "turningOff"


class MicrowaveDoorStatus(Enum):
    Open = "open"
    Closed = "closed"


class HoodFanSpeed(Enum):
    Off = "off"
    Low = "low"
    Medium = "med"
    High = "high"
    Boost = "boost"


class HoodLightLevel(Enum):
    Off = "off"
    Low = "low"
    Medium = "med"
    High = "high"


class HoodLightColor(Enum):
    WarmWhite = "warmWhite"
    NaturalWhite = "naturalWhite"
    CoolWhite = "coolWhite"


class Microwave(Appliance, ABC):
    """Public API for a microwave oven. Implementations live in transport modules."""

    @abstractmethod
    def get_cavity_state(self) -> MicrowaveCavityState | None: ...

    @abstractmethod
    def get_door_status(self) -> MicrowaveDoorStatus | None: ...

    @abstractmethod
    def get_door_locked(self) -> bool | None: ...

    @abstractmethod
    def get_cavity_light(self) -> bool | None: ...

    @abstractmethod
    async def set_cavity_light(self, on: bool) -> bool: ...

    @abstractmethod
    def get_display_temperature(self) -> float | None: ...

    @abstractmethod
    def get_display_temperature_unit(self) -> str | None: ...

    @abstractmethod
    def get_turntable_enabled(self) -> bool | None: ...

    @abstractmethod
    def get_active_recipe_id(self) -> str | None: ...

    @abstractmethod
    def get_recipe_execution_state(self) -> str | None: ...

    @abstractmethod
    def get_mwo_power_level(self) -> int | None: ...

    @abstractmethod
    def get_cook_timer_state(self) -> str | None: ...

    @abstractmethod
    def get_cook_timer_total_seconds(self) -> int | None: ...

    @abstractmethod
    def get_cook_timer_time_complete(self) -> int | None: ...

    @abstractmethod
    def get_hood_light_level(self) -> HoodLightLevel | None: ...

    @abstractmethod
    def get_hood_light_color(self) -> HoodLightColor | None: ...

    @abstractmethod
    def get_hood_fan_speed(self) -> HoodFanSpeed | None: ...

    @abstractmethod
    def get_remote_start_enabled(self) -> bool | None: ...

    @abstractmethod
    def get_control_locked(self) -> bool | None: ...

    @abstractmethod
    def get_quiet_mode(self) -> bool | None: ...

    @abstractmethod
    def get_sabbath_mode(self) -> bool | None: ...
