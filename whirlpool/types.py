from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Brand(Enum):
    Whirlpool = 0
    Maytag = 1
    KitchenAid = 2
    Consul = 3


class Region(Enum):
    EU = 0
    US = 1


@dataclass
class ApplianceInfo:
    said: str
    name: str
    category: str
    model_number: str
    serial_number: str
    raw_info: dict[str, Any] = field(default_factory=dict, repr=False)
