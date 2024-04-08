import logging

from .types import Brand, CredentialsDict, Region

LOGGER = logging.getLogger(__name__)

CREDENTIALS: dict[Brand, list[CredentialsDict]] = {
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
}

URLS: dict[Region, str] = {
    Region.EU: "https://prod-api.whrcloud.eu",
    Region.US: "https://api.whrcloud.com",
}

BACKEND_DATA = CREDENTIALS | URLS


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
        return URLS[self._region]

    @property
    def client_credentials(self) -> list[CredentialsDict]:
        return CREDENTIALS[self._brand]

    @property
    def auth_url(self):
        return f"{self.base_url}/oauth/token"

    @property
    def ws_url(self):
        return f"{self.base_url}/api/v1/client_auth/webSocketUrl"

    @property
    def post_appliance_command_url(self):
        return f"{self.base_url}/api/v1/appliance/command"

    @property
    def get_appliance_data_url(self):
        return f"{self.base_url}/api/v1/appliance"

    @property
    def get_user_data_url(self):
        return f"{self.base_url}/api/v1/getUserDetails"

    @property
    def get_shared_appliances_url(self):
        return f"{self.base_url}/api/v1/share-accounts/appliances"

    @property
    def get_owned_appliances_url(self):
        return f"{self.base_url}/api/v2/appliance/all/account"
