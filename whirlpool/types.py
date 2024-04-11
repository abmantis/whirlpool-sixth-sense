from dataclasses import dataclass
from enum import Enum


class Brand(Enum):
    Whirlpool = 0
    Maytag = 1
    KitchenAid = 2


class Region(Enum):
    EU = 0
    US = 1


@dataclass
class ApplianceData:
    said: str
    name: str
    data_model: str
    category: str
    model_number: str
    serial_number: str