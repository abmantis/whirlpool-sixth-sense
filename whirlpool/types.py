from dataclasses import dataclass
from enum import Enum
from typing import TypedDict


class Brand(Enum):
    Whirlpool = 0
    Maytag = 1
    KitchenAid = 2
    Consul = 3


class Region(Enum):
    EU = 0
    US = 1


class ApplianceKind(Enum):
    AirCon = 0
    Dryer = 1
    Oven = 2
    Refrigerator = 3
    Washer = 4


@dataclass
class CredentialsDict(TypedDict):
    client_id: str
    client_secret: str


@dataclass
class ApplianceData:
    said: str
    name: str
    data_model: str
    category: str
    model_number: str
    serial_number: str

