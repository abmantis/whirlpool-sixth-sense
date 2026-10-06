from abc import ABC, abstractmethod
from enum import Enum

from .appliance import Appliance


class MachineState(Enum):
    Standby = 0
    Setting = 1
    DelayCountdownMode = 2
    DelayPause = 3
    SmartDelay = 4
    SmartGridPause = 5
    Pause = 6
    RunningMainCycle = 7
    RunningPostCycle = 8
    Exceptions = 9
    Complete = 10
    PowerFailure = 11
    ServiceDiagnostic = 12
    FactoryDiagnostic = 13
    LifeTest = 14
    CustomerFocusMode = 15
    DemoMode = 16
    HardStopOrError = 17
    SystemInit = 18


class Washer(Appliance, ABC):
    @abstractmethod
    def get_machine_state(self) -> MachineState | None:
        pass

    @abstractmethod
    def get_cycle_status_sensing(self) -> bool | None:
        pass

    @abstractmethod
    def get_cycle_status_filling(self) -> bool | None:
        pass

    @abstractmethod
    def get_cycle_status_soaking(self) -> bool | None:
        pass

    @abstractmethod
    def get_cycle_status_washing(self) -> bool | None:
        pass

    @abstractmethod
    def get_cycle_status_rinsing(self) -> bool | None:
        pass

    @abstractmethod
    def get_cycle_status_spinning(self) -> bool | None:
        pass

    @abstractmethod
    def get_dispense_1_level(self) -> int | None:
        pass

    @abstractmethod
    def get_door_open(self) -> bool | None:
        pass

    @abstractmethod
    def get_time_remaining(self) -> int | None:
        pass

    def get_remote_control_enabled(self) -> bool | None:
        """Return remote-control status when supported by this transport."""
        return None

    async def start(self) -> bool:
        """Start the current cycle when supported by this transport."""
        return False

    async def pause(self) -> bool:
        """Pause the current cycle when supported by this transport."""
        return False

    async def resume(self) -> bool:
        """Resume the current cycle when supported by this transport."""
        return False

    async def cancel(self) -> bool:
        """Cancel the current cycle when supported by this transport."""
        return False


    def get_dispense_2_level(self) -> int | None:
        return None

    def get_wash_cycle_pair(self) -> tuple[str, str] | None:
        return None

    def get_utility_cycle(self) -> str | None:
        return None

    def is_cycle_options_model_supported(self) -> bool:
        return False

    def cycle_select_changeable(self) -> bool | None:
        return None

    def temperature_changeable(self) -> bool | None:
        return None

    def spin_speed_changeable(self) -> bool | None:
        return None

    def soil_level_changeable(self) -> bool | None:
        return None

    def extra_rinse_changeable(self) -> bool | None:
        return None

    def presoak_changeable(self) -> bool | None:
        return None

    def supports_temperature(self) -> bool:
        return False

    def supports_spin_speed(self) -> bool:
        return False

    def supports_soil_level(self) -> bool:
        return False

    def supports_extra_rinse(self) -> bool:
        return False

    def supports_presoak(self) -> bool:
        return False

    def supports_utility_cycles(self) -> bool:
        return False

    def cycle_supports_temperature(self) -> bool:
        return False

    def cycle_supports_spin_speed(self) -> bool:
        return False

    def cycle_supports_soil_level(self) -> bool:
        return False

    def cycle_supports_extra_rinse(self) -> bool:
        return False

    def cycle_supports_presoak(self) -> bool:
        return False

    def cycle_supports_fan_fresh(self) -> bool:
        return False

    def cycle_supports_steam(self) -> bool:
        return False

    def get_supported_temperatures(self) -> list[str]:
        return []

    def get_supported_spin_speeds(self) -> list[str]:
        return []

    def get_supported_soil_levels(self) -> list[str]:
        return []

    def get_supported_extra_rinse_options(self) -> list[str]:
        return []

    def get_supported_presoak_options(self) -> list[str]:
        return []

    def get_temperature(self) -> str | None:
        return None

    def get_spin_speed(self) -> str | None:
        return None

    def get_soil_level(self) -> str | None:
        return None

    def get_extra_rinse(self) -> str | None:
        return None

    def get_presoak(self) -> str | None:
        return None

    async def set_temperature(self, option: str) -> bool:
        return False

    async def set_spin_speed(self, option: str) -> bool:
        return False

    async def set_soil_level(self, option: str) -> bool:
        return False

    async def set_extra_rinse(self, option: str) -> bool:
        return False

    async def set_presoak(self, option: str | int) -> bool:
        return False

    def is_fan_fresh_model_supported(self) -> bool:
        return False

    def supports_fan_fresh(self) -> bool:
        return False

    def get_fan_fresh(self) -> str | None:
        return None

    def fan_fresh_changeable(self) -> bool | None:
        return None

    async def set_fan_fresh(self, option: str) -> bool:
        return False

    def is_steam_model_supported(self) -> bool:
        return False

    def supports_steam(self) -> bool:
        return False

    def get_steam(self) -> str | None:
        return None

    def steam_changeable(self) -> bool | None:
        return None

    async def set_steam(self, option: str) -> bool:
        return False

    async def set_wash_cycle_pair(self, what: str, how: str) -> bool:
        return False

    async def set_wash_cycle_recipe(
        self,
        what: str,
        how: str,
        *,
        temperature: str | None = None,
        spin_speed: str | None = None,
        soil_level: str | None = None,
        extra_rinse: str | None = None,
        presoak: str | None = None,
        fan_fresh: str | None = None,
        steam: str | None = None,
    ) -> bool:
        return False

    async def set_utility_cycle(self, utility: str) -> bool:
        return False

    def get_dispense_1_enable(self) -> str | None:
        return None

    async def set_dispense_1_enable(self, option: str) -> bool:
        return False

    def get_dispense_2_enable(self) -> str | None:
        return None

    async def set_dispense_2_enable(self, option: str) -> bool:
        return False

    def get_dispense_1_concentration(self) -> str | None:
        return None

    async def set_dispense_1_concentration(self, option: str) -> bool:
        return False

    def get_dispense_2_concentration(self) -> str | None:
        return None

    async def set_dispense_2_concentration(self, option: str) -> bool:
        return False

    def get_dispense_2_selection(self) -> str | None:
        return None

    async def set_dispense_2_selection(self, option: str) -> bool:
        return False
