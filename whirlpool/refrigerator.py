import logging

import aiohttp

from .appliance import Appliance

LOGGER = logging.getLogger(__name__)

SETTING_TEMP = "Refrigerator_OpSetTempPreset"
SETTING_DISPLAY_LOCK = "Sys_OpSetControlLock"
SETTING_TURBO_MODE = "Sys_OpSetMaxCool"

TEMP_MAP = {
    -4: 12,
    -2: 11,
    0: 10,
    3: 9,
    5: 8,
}


class Refrigerator(Appliance):
    def __init__(self, backend_selector, auth, said, session: aiohttp.ClientSession):
        Appliance.__init__(self, backend_selector, auth, said, session)

    def get_current_temp(self, real_temp: bool = None):
        if real_temp:
            reversed_temp_map = {v: k for k, v in TEMP_MAP.items()}
            return str(reversed_temp_map[int(self.get_attribute(SETTING_TEMP))])
        return int(self.get_attribute(SETTING_TEMP))

    async def set_temp(self, temp: int):
        if 8 <= temp <= 12:
            await self.send_attributes({SETTING_TEMP: str(temp)})

    async def set_especific_temp(self, temp: int):
        allowed_temps = [-4, -2, 0, 3, 5]
        if temp not in allowed_temps:
            raise ValueError(
                f"Invalid temperature: {temp}. Allowed values are {allowed_temps}."
            )
        await self.send_attributes({SETTING_TEMP: str(TEMP_MAP[temp])})

    def get_turbo_mode(self):
        return self.attr_value_to_bool(self.get_attribute(SETTING_TURBO_MODE))

    async def set_turbo_mode(self, turbo: bool):
        await self.send_attributes({SETTING_TURBO_MODE: self.bool_to_attr_value(turbo)})

    def get_display_lock(self):
        return self.attr_value_to_bool(self.get_attribute(SETTING_DISPLAY_LOCK))

    async def set_display_lock(self, display: bool):
        await self.send_attributes(
            {SETTING_DISPLAY_LOCK: self.bool_to_attr_value(display)}
        )
