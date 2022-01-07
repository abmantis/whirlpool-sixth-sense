import logging
from enum import Enum

LOGGER = logging.getLogger(__name__)


class Brand(Enum):
    Whirlpool = 0
    Maytag = 1


BACKEND_DATA = {
    Brand.Whirlpool: {
        "base_url": "https://api.whrcloud.eu",
        "client_id": "whirlpool_android",
        "client_secret": "i-eQ8MD4jK4-9DUCbktfg-t_7gvU-SrRstPRGAYnfBPSrHHt5Mc0MFmYymU2E2qzif5cMaBYwFyFgSU6NTWjZg",
    },
    Brand.Maytag: {
        "base_url": "https://api.whrcloud.com",
        "client_id": "maytag_ios",
        "client_secret": "OfTy3A3rV4BHuhujkPThVDE9-SFgOymJyUrSbixjViATjCGviXucSKq2OxmPWm8DDj9D1IFno_mZezTYduP-Ig",
    },
}


class BackendSelector:
    def __init__(self, brand: Brand):
        self._brand = brand

    @property
    def brand(self):
        return self._brand

    @property
    def base_url(self):
        return BACKEND_DATA[self._brand].get("base_url")

    @property
    def client_id(self):
        return BACKEND_DATA[self._brand].get("client_id")

    @property
    def client_secret(self):
        return BACKEND_DATA[self._brand].get("client_secret")
