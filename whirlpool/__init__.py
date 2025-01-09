"""
    Import all devices here. This forces their classes to be
    added to the registry before the AppliancesManager object
    is created.
"""

from .aircon import Aircon
from .dryer import Dryer
from .oven import Oven
from .refrigerator import Refrigerator
from .washer import Washer

