import logging
from enum import Enum
from typing import List, TypedDict

LOGGER = logging.getLogger(__name__)


class CredentialsDict(TypedDict):
    client_id: str
    client_secret: str


class Brand(Enum):
    Whirlpool = 0
    Maytag = 1
    KitchenAid = 2


class Region(Enum):
    EU = 0
    US = 1


BACKEND_DATA = {
    Brand.Whirlpool: [
        {
            "client_id": "whirlpool_android",
            "client_secret": "i-eQ8MD4jK4-9DUCbktfg-t_7gvU-SrRstPRGAYnfBPSrHHt5Mc0MFmYymU2E2qzif5cMaBYwFyFgSU6NTWjZg",
        },
        {
            "client_id": "Whirlpool_Android",
            "client_secret": "784f6b9432727d5967a56e1ac6b125839cb0b789a52c47f450c98b2acaa4fdce",
        },
    ],
    Brand.Maytag: [
        {
            "client_id": "maytag_ios",
            "client_secret": "OfTy3A3rV4BHuhujkPThVDE9-SFgOymJyUrSbixjViATjCGviXucSKq2OxmPWm8DDj9D1IFno_mZezTYduP-Ig",
        }
    ],
    Brand.KitchenAid: [
        {
            "client_id": "Kitchenaid_iOS",
            "client_secret": "kkdPquOHfNH-iIinccTdhAkJmaIdWBhLehhLrfoXRWbKjEpqpdu92PISF_yJEWQs72D2yeC0PdoEKeWgHR9JRA",
        }
    ],
    Region.EU: {"base_url": "https://prod-api.whrcloud.eu"},
    Region.US: {"base_url": "https://api.whrcloud.com"},
}


class BackendSelector:
    def __init__(self, brand: Brand, region: Region):
        self._brand = brand
        self._region = region

    @property
    def brand(self):
        return self._brand

    @property
    def region(self):
        return self._region

    @property
    def base_url(self):
        return BACKEND_DATA[self._region].get("base_url")

    @property
    def client_credentials(self) -> List[CredentialsDict]:
        return BACKEND_DATA[self._brand]

    @property
    def auth_url(self):
        return f"{self.base_url}/oauth/token"
