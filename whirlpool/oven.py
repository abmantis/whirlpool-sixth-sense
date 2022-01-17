import logging
from enum import Enum
from typing import Callable

from .appliance import Appliance

LOGGER = logging.getLogger(__name__)

ATTR_DISPLAY_MEAT_PROBE_STATUS = "OvenUpperCavity_DisplStatusMeatProbeDisplayTemp"

class Oven(Appliance):
    def __init__(self, backend_selector, auth, said, attr_changed: Callable):
        Appliance.__init__(self, backend_selector, auth, said, attr_changed)

    def get_meat_probe_status(self):
        return self.attr_value_to_bool(self.get_attribute(ATTR_DISPLAY_MEAT_PROBE_STATUS))
