import logging
from enum import Enum

LOGGER = logging.getLogger(__name__)


class Brand(Enum):
    Whirlpool = 0
    Maytag = 1

class Region(Enum):
    EU = 0
    US = 1


BACKEND_DATA = {
    Brand.Whirlpool: {
        "client_id": "whirlpool_android",
        "client_secret": "i-eQ8MD4jK4-9DUCbktfg-t_7gvU-SrRstPRGAYnfBPSrHHt5Mc0MFmYymU2E2qzif5cMaBYwFyFgSU6NTWjZg",
    },
    Brand.Maytag: {
        "client_id": "maytag_ios",
        "client_secret": "OfTy3A3rV4BHuhujkPThVDE9-SFgOymJyUrSbixjViATjCGviXucSKq2OxmPWm8DDj9D1IFno_mZezTYduP-Ig",
    },
    Region.EU: {
        "base_url": "https://api.whrcloud.eu"
    },
    Region.US: {
        "base_url": "https://api.whrcloud.com"
    },
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
    def client_id(self):
        return BACKEND_DATA[self._brand].get("client_id")

    @property
    def client_secret(self):
        return BACKEND_DATA[self._brand].get("client_secret")
