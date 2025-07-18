import logging
from enum import Enum

from .appliance import Appliance

LOGGER = logging.getLogger(__name__)

ATTR_MODE = "Cavity_OpStatusMode"
ATTR_DISPLAY_TEMP = "Sys_OpStatusDisplayTemp"
ATTR_DISPLAY_HUMID = "Sys_OpStatusDisplayHumidity"

SETTING_REBOOT_WIFI = "XCat_WifiSetRebootWifiCommModule"
SETTING_POWER = "Sys_OpSetPowerOn"
SETTING_TEMP = "Sys_OpSetTargetTemp"
SETTING_HUMIDITY = "Sys_OpSetTargetHumidity"
SETTING_SLEEP_MODE = "Sys_OpSetSleepMode"
SETTING_HORZ_LOUVER_SWING = "Cavity_OpSetHorzLouverSwing"
SETTING_MODE = "Cavity_OpSetMode"
SETTING_FAN_SPEED = "Cavity_OpSetFanSpeed"
SETTING_TURBO_MODE = "Cavity_OpSetTurboMode"
SETTING_ECO_MODE = "Sys_OpSetEcoModeEnabled"
SETTING_QUIET_MODE = "Sys_OpSetQuietModeEnabled"
SETTING_DISPLAY_BRIGHTNESS = "Sys_DisplaySetBrightness"

ATTRVAL_MODE_COOL = "1"
ATTRVAL_MODE_FAN = "2"
ATTRVAL_MODE_HEAT = "3"
ATTRVAL_MODE_SIXTH_SENSE_AIR = "5"
ATTRVAL_MODE_SIXTH_SENSE_HEAT = "6"
ATTRVAL_MODE_SIXTH_SENSE_COOL = "7"

SETVAL_MODE_COOL = "1"
SETVAL_MODE_FAN = "2"
SETVAL_MODE_HEAT = "3"
SETVAL_MODE_SIXTH_SENSE = "4"
SETVAL_FAN_SPEED_OFF = "0"
SETVAL_FAN_SPEED_AUTO = "1"
SETVAL_FAN_SPEED_LOW = "2"
SETVAL_FAN_SPEED_MEDIUM = "4"
SETVAL_FAN_SPEED_HIGH = "6"
SETVAL_DISPLAY_BRIGHTNESS_OFF = "0"
SETVAL_DISPLAY_BRIGHTNESS_ON = "4"
SETVAL_SLEEP_MODE_OFF = "0"
SETVAL_SLEEP_MODE_ADULTS = "1"
SETVAL_SLEEP_MODE_ELDERLY = "2"
SETVAL_SLEEP_MODE_TEENS = "3"
SETVAL_SLEEP_MODE_CHILDREN = "4"


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


MODES_MAP = {
    Mode.Cool: SETVAL_MODE_COOL,
    Mode.Heat: SETVAL_MODE_HEAT,
    Mode.Fan: SETVAL_MODE_FAN,
    Mode.SixthSense: SETVAL_MODE_SIXTH_SENSE,
}

FANSPEED_MAP = {
    FanSpeed.Off: SETVAL_FAN_SPEED_OFF,
    FanSpeed.Auto: SETVAL_FAN_SPEED_AUTO,
    FanSpeed.Low: SETVAL_FAN_SPEED_LOW,
    FanSpeed.Medium: SETVAL_FAN_SPEED_MEDIUM,
    FanSpeed.High: SETVAL_FAN_SPEED_HIGH,
}


class Aircon(Appliance):
    def get_current_temp(self) -> float | None:
        raw_temp = self._get_int_attribute(ATTR_DISPLAY_TEMP)
        return raw_temp / 10 if raw_temp is not None else None

    def get_current_humidity(self) -> int | None:
        return self._get_int_attribute(ATTR_DISPLAY_HUMID)

    def get_power_on(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(SETTING_POWER))

    async def set_power_on(self, on: bool) -> bool:
        return await self.send_attributes({SETTING_POWER: self.bool_to_attr_value(on)})

    def get_temp(self) -> float | None:
        raw_temp = self._get_int_attribute(SETTING_TEMP)
        return raw_temp / 10 if raw_temp is not None else None

    async def set_temp(self, temp: float) -> bool:
        tempint = int(temp * 10)
        return await self.send_attributes({SETTING_TEMP: str(tempint)})

    def get_humidity(self) -> int | None:
        return self._get_int_attribute(SETTING_HUMIDITY)

    async def set_humidity(self, temp: int) -> bool:
        return await self.send_attributes({SETTING_HUMIDITY: str(temp)})

    def get_mode(self) -> Mode | None:
        mode_raw = self._get_attribute(ATTR_MODE)
        if mode_raw in [ATTRVAL_MODE_COOL, ATTRVAL_MODE_SIXTH_SENSE_COOL]:
            return Mode.Cool
        if mode_raw in [ATTRVAL_MODE_HEAT, ATTRVAL_MODE_SIXTH_SENSE_HEAT]:
            return Mode.Heat
        if mode_raw in [ATTRVAL_MODE_FAN, ATTRVAL_MODE_SIXTH_SENSE_AIR]:
            return Mode.Fan
        return None

    def get_sixthsense_mode(self) -> bool:
        return self._get_attribute(SETTING_MODE) == SETVAL_MODE_SIXTH_SENSE

    async def set_mode(self, mode: Mode) -> bool:
        if mode not in MODES_MAP:
            raise ValueError("Invalid mode")
        return await self.send_attributes({SETTING_MODE: MODES_MAP[mode]})

    def get_fanspeed(self) -> FanSpeed | None:
        fanspeed_raw = self._get_attribute(SETTING_FAN_SPEED)
        for k, v in FANSPEED_MAP.items():
            if v == fanspeed_raw:
                return k
        return None

    async def set_fanspeed(self, speed: FanSpeed) -> bool:
        if speed not in FANSPEED_MAP:
            raise ValueError("Invalid fan speed")
        return await self.send_attributes({SETTING_FAN_SPEED: FANSPEED_MAP[speed]})

    def get_h_louver_swing(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(SETTING_HORZ_LOUVER_SWING))

    async def set_h_louver_swing(self, swing: bool) -> bool:
        return await self.send_attributes(
            {SETTING_HORZ_LOUVER_SWING: self.bool_to_attr_value(swing)}
        )

    def get_turbo_mode(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(SETTING_TURBO_MODE))

    async def set_turbo_mode(self, turbo: bool) -> bool:
        return await self.send_attributes(
            {SETTING_TURBO_MODE: self.bool_to_attr_value(turbo)}
        )

    def get_eco_mode(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(SETTING_ECO_MODE))

    async def set_eco_mode(self, eco: bool) -> bool:
        return await self.send_attributes(
            {SETTING_ECO_MODE: self.bool_to_attr_value(eco)}
        )

    def get_quiet_mode(self) -> bool | None:
        return self.attr_value_to_bool(self._get_attribute(SETTING_QUIET_MODE))

    async def set_quiet_mode(self, quiet: bool) -> bool:
        return await self.send_attributes(
            {SETTING_QUIET_MODE: self.bool_to_attr_value(quiet)}
        )

    def get_display_on(self) -> bool | None:
        return (
            self._get_attribute(SETTING_DISPLAY_BRIGHTNESS)
            == SETVAL_DISPLAY_BRIGHTNESS_ON
        )

    async def set_display_on(self, on: bool) -> bool:
        bri = SETVAL_DISPLAY_BRIGHTNESS_ON if on else SETVAL_DISPLAY_BRIGHTNESS_OFF
        return await self.send_attributes({SETTING_DISPLAY_BRIGHTNESS: bri})
