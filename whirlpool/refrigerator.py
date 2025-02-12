import logging

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
    def get_offset_temp(self) -> int | None:
        reversed_temp_map = {v: k for k, v in TEMP_MAP.items()}
        raw_temp = self.get_int_attribute(SETTING_TEMP)
        return reversed_temp_map[raw_temp] if raw_temp is not None else None

    async def set_offset_temp(self, temp):
        if temp in TEMP_MAP.keys():
            await self.send_attributes({SETTING_TEMP: str(TEMP_MAP[temp])})
        else:
            LOGGER.error(
                f"Invalid temperature: {temp}. Allowed values are {TEMP_MAP.keys()}."
            )

    def get_temp(self) -> int | None:
        return self.get_int_attribute(SETTING_TEMP)

    async def set_temp(self, temp: int):
        if temp in TEMP_MAP.values():
            await self.send_attributes({SETTING_TEMP: str(temp)})
        else:
            LOGGER.error(
                f"Invalid temperature: {temp}. Allowed values are {TEMP_MAP.values()}."
            )

    def get_turbo_mode(self) -> bool | None:
        return self.attr_value_to_bool(self.get_attribute(SETTING_TURBO_MODE))

    async def set_turbo_mode(self, turbo: bool):
        await self.send_attributes({SETTING_TURBO_MODE: self.bool_to_attr_value(turbo)})

    def get_display_lock(self) -> bool | None:
        return self.attr_value_to_bool(self.get_attribute(SETTING_DISPLAY_LOCK))

    async def set_display_lock(self, display: bool):
        await self.send_attributes(
            {SETTING_DISPLAY_LOCK: self.bool_to_attr_value(display)}
        )
