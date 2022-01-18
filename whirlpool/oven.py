import logging
from enum import Enum
from typing import Callable

from .appliance import Appliance

LOGGER = logging.getLogger(__name__)

ATTR_DISPLAY_MEAT_PROBE_STATUS = "OvenUpperCavity_DisplStatusMeatProbeDisplayTemp"
ATTR_DISPLAY_BRIGHTNESS = "Sys_DisplaySetBrightnessPercent"
ATTR_CONTROL_LOCK = "Sys_OperationSetControlLock"

ATTR_POSTFIX_DOOR_OPEN_STATUS = "OpStatusDoorOpen"

class Cavity(Enum):
    Upper = 0
    Lower = 1

CAVITY_PREFIX_MAP = {
    Cavity.Upper: "OvenUpperCavity",
    Cavity.Lower: "OvenLowerCavity"
}

class Oven(Appliance):
    def __init__(self, backend_selector, auth, said, attr_changed: Callable):
        Appliance.__init__(self, backend_selector, auth, said, attr_changed)

    def get_meat_probe_status(self):
        return self.attr_value_to_bool(self.get_attribute(ATTR_DISPLAY_MEAT_PROBE_STATUS))

    def get_door_opened(self, cavity: Cavity = Cavity.Upper):
        return self.attr_value_to_bool(self.get_attribute(CAVITY_PREFIX_MAP[cavity] + "_" + ATTR_POSTFIX_DOOR_OPEN_STATUS))

    def get_display_brightness_percent(self):
        return self.get_attribute(ATTR_DISPLAY_BRIGHTNESS)

    async def set_display_brightness_percent(self, pct: int):
        await self.send_attributes({ATTR_DISPLAY_BRIGHTNESS: str(pct)})

    def get_control_locked(self):
        return self.attr_value_to_bool(self.get_attribute(ATTR_CONTROL_LOCK))

    async def set_control_locked(self, on: bool):
        await self.send_attributes({ATTR_CONTROL_LOCK: self.bool_to_attr_value(on)})

