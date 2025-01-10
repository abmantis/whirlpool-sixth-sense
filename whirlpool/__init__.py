"""
    Import all devices here. This forces their classes to be
    added to the registry before the AppliancesManager object
    is created.
"""

from .aircon import Aircon as Aircon
from .dryer import Dryer as Dryer
from .oven import Oven as Oven
from .refrigerator import Refrigerator as Refrigerator
from .washer import Washer as Washer


