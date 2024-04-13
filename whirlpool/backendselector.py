import logging

from .types import Brand, Region

LOGGER = logging.getLogger(__name__)

CREDENTIALS: dict[Brand, list[dict[str, str]]] = {
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
    def brand(self) -> Brand:
        return self._brand

    @property
    def region(self) -> Region:
        return self._region

    @property
    def base_url(self) -> str:
        return URLS[self._region]

    @property
    def client_credentials(self) -> list[dict[str, str]]:
        return CREDENTIALS[self._brand]

    @property
    def appliance_command_url(self) -> str:
        return f"{self.base_url}/api/v1/appliance/command"

    @property
    def oauth_token_url(self) -> str:
        return f"{self.base_url}/oauth/token"

    @property
    def websocket_url(self) -> str:
        return f"{self.base_url}/api/v1/client_auth/webSocketUrl"

    @property
    def user_details_url(self) -> str:
        return f"{self.base_url}/api/v1/getUserDetails"

    @property
    def shared_appliances_url(self) -> str:
        return f"{self.base_url}/api/v1/share-accounts/appliances"

    def get_appliance_data_url(self, said: str) -> str:
        return f"{self.base_url}/api/v1/appliance/{said}"

    def get_owned_appliances_url(self, account_id: str) -> str:
        return f"{self.base_url}/api/v2/appliance/all/account/{account_id}"
