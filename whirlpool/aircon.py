import logging
from enum import Enum

from .appliance import Appliance

ATTR_ONLINE = "Online"
ATTR_MODE = "Cavity_OpStatusMode"
ATTR_TEMP = "Sys_OpStatusDisplayTemp",
ATTR_HUMID = "Sys_OpStatusDisplayHumidity",

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

class Modes(Enum):
    Cool = 1
    Heat = 2
    Fan = 3
    SixthSense = 4


MODES_MAP = {Modes.Cool: SETVAL_MODE_COOL,
             Modes.Heat: SETVAL_MODE_HEAT,
             Modes.Fan: SETVAL_MODE_FAN,
             Modes.SixthSense: SETVAL_MODE_SIXTH_SENSE,
             }

class Aircon(Appliance):
    def __init__(self, auth, said):
        Appliance.__init__(self, auth, said)

    def print_fetched_data(self):
        attrs = [
                "Online",
                "Sys_OpSetPowerOn",
                "Sys_OpSetTargetTemp",
                "Sys_OpSetTargetHumidity",
                "Sys_OpSetSleepMode",
                "Cavity_OpSetHorzLouverSwing",
                "Cavity_OpSetMode",
                "Cavity_OpSetFanSpeed",
                "Cavity_OpSetTurboMode",
                "Sys_OpSetEcoModeEnabled",
                "Sys_OpSetQuietModeEnabled",
                "Cavity_OpStatusMode",
                "Sys_OpStatusDisplayTemp",
                "Sys_OpStatusDisplayHumidity",
            ]

        for a in attrs:
            print(a + ": " + self.get_attribute_from_fetched_data(a))

    def online(self):
        return self._data_dict["Online"]

    def turn_on(self):
        self.send_attributes({SETTING_POWER: SETVAL_VALUE_ON})

    def turn_off(self):
        self.send_attributes({SETTING_POWER: SETVAL_VALUE_OFF})

    def set_temp(self, temp: int):
        self.send_attributes({SETTING_TEMP: str(temp)})

    def set_mode(self, mode: Modes):
        if mode not in MODES_MAP:
            logging.error("Invalid moed")
        self.send_attributes({SETTING_MODE: MODES_MAP[mode]})
