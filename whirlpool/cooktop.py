import logging
from enum import Enum
from typing import Callable

from .appliance import Appliance

LOGGER = logging.getLogger(__name__)


class ElementNotification(Enum):
    Nothing = 1
    BoilDry = 2
    BoilOver = 3
    NoPan = 4
    HotArea = 5


class ElementState(Enum):
    Idle = 1
    Running = 2
    Pause = 3
    Complete = 4


class State(Enum):
    Off = 1
    Programming = 2
    Running = 3


ATTR_ONLINE = "Online"
ATTR_ELEMENT_NOTIFICATION = "Cooktop_AlertStatusCookElementNotification"
ATTR_ELEMENT_STATE = "Cooktop_CycleStatusCookElementState"
ATTR_ELEMENT_TIME_ELAPSED = "Cooktop_TimeStatusCookElementTimeElapsed"
ATTR_ELEMENT_TIME_REMAINING = "Cooktop_TimeStatusCookElementTimeRemaining"
ATTR_ELEMENT_PERCENT_COMPLETE = "Cooktop_TimeStatusCookElementPercentComplete"
ATTR_STATE = "Cooktop_OperationStatusState"

SETTING_REBOOT_WIFI = "XCat_WifiSetRebootWifiCommModule"
SETTING_ELEMENT_OPERATIONS = "Cooktop_OperationSetCookElementOperations"
SETTING_ELEMENT_POWER = "Cooktop_CycleSetCookElementPower"
SETTING_MODE = "Cooktop_OperationSetCooktopMode"
SETTING_AREA = "Cooktop_CycleSetCookArea"
SETTING_ELEMENT_TIME = "Cooktop_TimeSetCookElementTimeSet"
SETTING_CONTROL_LOCK = "Sys_OperationSetControlLock"

SETVAL_VALUE_OFF = "0"
SETVAL_VALUE_ON = "1"

ATTRVALS = {
    ATTR_ELEMENT_NOTIFICATION: {
        "0": ElementNotification.Nothing,
        "1": ElementNotification.BoilDry,
        "2": ElementNotification.BoilOver,
        "3": ElementNotification.NoPan,
        "4": ElementNotification.HotArea,
    },
    ATTR_ELEMENT_STATE: {
        "0": ElementState.Idle,
        "1": ElementState.Running,
        "2": ElementState.Pause,
        "3": ElementState.Complete,
    },
    ATTR_STATE: {
        "0": State.Off,
        "1": State.Programming,
        "2": State.Running,
    },
    SETTING_ELEMENT_OPERATIONS: {},
    SETTING_ELEMENT_POWER: {},
    SETTING_MODE: {},
    SETTING_AREA: {},
    SETTING_ELEMENT_TIME: {},
    SETTING_CONTROL_LOCK: {},
}


class Cookop(Appliance):
    def __init__(self, auth, said, attr_changed: Callable):
        Appliance.__init__(self, auth, said, attr_changed)

    def _bool_to_attr_value(self, b: bool):
        return SETVAL_VALUE_ON if b else SETVAL_VALUE_OFF

    def _attr_value_to_bool(self, val: str):
        return val == SETVAL_VALUE_ON

    def _split_elements(self, data: str):
        return data.rstrip(",").split(",")

    def _elements_to_enum(self, elements: list, mapping: dict):
        return [mapping.get(elem, None) for elem in elements]

    def _get_enum_elements_attribute(self, attribute):
        return self._elements_to_enum(
            self._split_elements(self.get_attribute(attribute)), ATTRVALS[attribute]
        )

    def get_online(self):
        return self._attr_value_to_bool(self.get_attribute(ATTR_ONLINE))

    def get_element_notification(self):
        return self._get_enum_elements_attribute(ATTR_ELEMENT_NOTIFICATION)

    def get_element_state(self):
        return self._get_enum_elements_attribute(ATTR_ELEMENT_STATE)

    def get_element_time_elapsed(self):
        return self._split_elements(self.get_attribute(ATTR_ELEMENT_TIME_ELAPSED))

    def get_element_time_remaining(self):
        return self._split_elements(self.get_attribute(ATTR_ELEMENT_TIME_REMAINING))

    def get_element_percent_complete(self):
        return self._split_elements(self.get_attribute(ATTR_ELEMENT_PERCENT_COMPLETE))

    def get_state(self):
        notif_id = self.get_attribute(ATTR_STATE)
        return ATTRVALS[ATTR_STATE].get(notif_id, None)
