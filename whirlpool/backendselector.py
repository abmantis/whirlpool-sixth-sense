import logging

from .types import Brand, Region

LOGGER = logging.getLogger(__name__)

CREDENTIALS: dict[Brand, list[dict[str, str]]] = {
    Brand.Whirlpool: [
        {
            "client_id": "whirlpool_emea_android_v1",
            "client_secret": "h-NBGuG7EY74sSvj9TrJeeTpodJBd4T35bAyV0mfa0YnJ0i4MBue8IiS4iFidkve",  # noqa: E501
        },
        {
            "client_id": "whirlpool_android_v1",
            "client_secret": "yH5BcCm4ogWBoyD_NrlE04vmVps2s8T7KaIi4PYrc_fsdphWpG1IwlLSJ-yl7FGV",  # noqa: E501
        },
    ],
    Brand.Maytag: [
        {
            "client_id": "maytag_android_v1",
            "client_secret": "f1XfYji_D9KfZGovyp8PMgRzrFKjhjY26TV0hu3Mt1-tCCNPl9s95z7QLUfB9UgB",  # noqa: E501
        }
    ],
    Brand.KitchenAid: [
        {
            "client_id": "kitchenaid_android_stg",
            "client_secret": "Dn-ukFAFoSWOnB9nVm7Y2DDj4Gs9Bocm6aOkhy0mdNGBj5RcoLkRfCXujuxpKrqF2w15sl1tI45JXwK5Zi4saw",  # noqa: E501
        },
        {
            "client_id": "kitchenaid_android_v1",
            "client_secret": "T5j9T4ZAMnC6EMVpPAwZyKsRykXGfKOMDqikPHYpCKEMYjssPtJtuJtMYEc30g56",  # noqa: E501
        },
    ],
    Brand.Consul: [
        {
            "client_id": "consul_lar_android_v1",
            "client_secret": "xfPIj2fqhHXlK4bz2oPToDX5E0zHZ409ZLY6ZHiU3p_jh4wv_Ycg8haUhnB6yXuA",  # noqa: E501
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
