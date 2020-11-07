import logging
from enum import Enum

from .appliance import Appliance

ATTR_ONLINE = "Online"
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

SETVAL_VALUE_OFF = "0"
SETVAL_VALUE_ON = "1"
SETVAL_MODE_COOL = "1"
SETVAL_MODE_FAN = "2"
SETVAL_MODE_HEAT = "3"
SETVAL_MODE_SIXTH_SENSE = "4"
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
    Auto = 1
    Low = 2
    Medium = 3
    High = 4


MODES_MAP = {Mode.Cool: SETVAL_MODE_COOL,
             Mode.Heat: SETVAL_MODE_HEAT,
             Mode.Fan: SETVAL_MODE_FAN,
             Mode.SixthSense: SETVAL_MODE_SIXTH_SENSE,
             }

FANSPEED_MAP = {FanSpeed.Auto: SETVAL_FAN_SPEED_AUTO,
                FanSpeed.Low: SETVAL_FAN_SPEED_LOW,
                FanSpeed.Medium: SETVAL_FAN_SPEED_MEDIUM,
                FanSpeed.High: SETVAL_FAN_SPEED_HIGH,
                }


class Aircon(Appliance):
    def __init__(self, auth, said):
        Appliance.__init__(self, auth, said)

    def _boolToAttrValue(self, b: bool):
        return SETVAL_VALUE_ON if b else SETVAL_VALUE_OFF

    def _attrValueToBool(self, val: str):
        return val == SETVAL_VALUE_ON

    def get_online(self):
        return self._attrValueToBool(self.get_attribute(ATTR_ONLINE))

    def get_current_temp(self):
        return int(self.get_attribute(ATTR_DISPLAY_TEMP)) / 10

    def get_current_humidity(self):
        return int(self.get_attribute(ATTR_DISPLAY_HUMID))

    def get_power_on(self):
        return self._attrValueToBool(self.get_attribute(SETTING_POWER))

    def set_power_on(self, on: bool):
        self.send_attributes({SETTING_POWER: self._boolToAttrValue(on)})

    def get_temp(self):
        return int(self.get_attribute(SETTING_TEMP)) / 10

    def set_temp(self, temp: float):
        tempint = int(temp * 10)
        self.send_attributes({SETTING_TEMP: str(tempint)})

    def get_humidity(self):
        return int(self.get_attribute(SETTING_HUMIDITY))

    def set_humidity(self, temp: int):
        self.send_attributes({SETTING_HUMIDITY: str(temp)})

    def get_mode(self):
        mode_raw = self.get_attribute(ATTR_MODE)
        if mode_raw in [ATTRVAL_MODE_COOL, ATTRVAL_MODE_SIXTH_SENSE_COOL]:
            return Mode.Cool
        if mode_raw in [ATTRVAL_MODE_HEAT, ATTRVAL_MODE_SIXTH_SENSE_HEAT]:
            return Mode.Heat
        if mode_raw in [ATTRVAL_MODE_FAN, ATTRVAL_MODE_SIXTH_SENSE_AIR]:
            return Mode.Fan

    def get_sixthsense_mode(self):
        return self.get_attribute(SETTING_MODE) == SETVAL_MODE_SIXTH_SENSE

    def set_mode(self, mode: Mode):
        if mode not in MODES_MAP:
            logging.error("Invalid mode")
        self.send_attributes({SETTING_MODE: MODES_MAP[mode]})

    def get_fanspeed(self):
        fanspeed_raw = self.get_attribute(SETTING_FAN_SPEED)
        for k, v in FANSPEED_MAP.items():
            if v == fanspeed_raw:
                return k
        return None

    def set_fanspeed(self, speed: FanSpeed):
        if speed not in FANSPEED_MAP:
            logging.error("Invalid fan speed")
        self.send_attributes({SETTING_MODE: FANSPEED_MAP[speed]})

    def get_h_louver_swing(self):
        return self._attrValueToBool(self.get_attribute(SETTING_HORZ_LOUVER_SWING))

    def set_h_louver_swing(self, swing: bool):
        self.send_attributes(
            {SETTING_HORZ_LOUVER_SWING: self._boolToAttrValue(swing)})

    def get_turbo_mode(self):
        return self._attrValueToBool(self.get_attribute(SETTING_TURBO_MODE))

    def set_turbo_mode(self, turbo: bool):
        self.send_attributes(
            {SETTING_TURBO_MODE: self._boolToAttrValue(turbo)})

    def get_eco_mode(self):
        return self._attrValueToBool(self.get_attribute(SETTING_ECO_MODE))

    def set_eco_mode(self, eco: bool):
        self.send_attributes(
            {SETTING_ECO_MODE: self._boolToAttrValue(eco)})

    def get_quiet_mode(self):
        return self._attrValueToBool(self.get_attribute(SETTING_QUIET_MODE))

    def set_quiet_mode(self, quiet: bool):
        self.send_attributes(
            {SETTING_QUIET_MODE: self._boolToAttrValue(quiet)})

    def get_display_on(self):
        return self.get_attribute(SETTING_DISPLAY_BRIGHTNESS) == SETVAL_DISPLAY_BRIGHTNESS_ON

    def set_display_on(self, on: bool):
        bri = SETVAL_DISPLAY_BRIGHTNESS_ON if on else SETVAL_DISPLAY_BRIGHTNESS_OFF
        self.send_attributes({SETTING_DISPLAY_BRIGHTNESS: bri})
