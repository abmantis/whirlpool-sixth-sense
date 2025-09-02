import logging
from dataclasses import dataclass

from .types import Brand, Region

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class BackendConfig:
    client_id: str
    client_secret: str


CREDENTIALS: dict[Region, dict[Brand, list[BackendConfig]]] = {
    Region.EU: {
        Brand.Whirlpool: [
            BackendConfig(
                client_id="whirlpool_emea_android_v2",
                client_secret="90_3TBRfXfcdCYJj6L5BThEqOBZNkEchrTPT7loqm0gBS_tyeFIIEv47mmYTZkb6",  # noqa: E501
            ),
        ],
        Brand.KitchenAid: [
            BackendConfig(
                client_id="kitchenaid_android_stg",
                client_secret="Dn-ukFAFoSWOnB9nVm7Y2DDj4Gs9Bocm6aOkhy0mdNGBj5RcoLkRfCXujuxpKrqF2w15sl1tI45JXwK5Zi4saw",  # noqa: E501
            ),
        ],
        Brand.Consul: [
            BackendConfig(
                client_id="consul_lar_android_v1",
                client_secret="xfPIj2fqhHXlK4bz2oPToDX5E0zHZ409ZLY6ZHiU3p_jh4wv_Ycg8haUhnB6yXuA",  # noqa: E501
            )
        ],
    },
    Region.US: {
        Brand.Whirlpool: [
            BackendConfig(
                client_id="whirlpool_android_v2",
                client_secret="rMVCgnKKhIjoorcRa7cpckh5irsomybd4tM9Ir3QxJxQZlzgWSeWpkkxmsRg1PL-",  # noqa: E501
            ),
        ],
        Brand.Maytag: [
            BackendConfig(
                client_id="maytag_android_v2",
                client_secret="ULTqdvvqK0O9XcSLO3nA2tJDTLFKxdaaeKrimPYdXvnLX_yUtPhxovESldBId0Tf",  # noqa: E501
            )
        ],
        Brand.KitchenAid: [
            BackendConfig(
                client_id="kitchenaid_android_v2",
                client_secret="jd15ExiJdEt8UgLWBslwkzkQkmRGCR9lVSgeaqcPmFZQc9pgxtpjmaPSw3g-aRXG",  # noqa: E501
            ),
        ],
        Brand.Consul: [
            BackendConfig(
                client_id="consul_lar_android_v1",
                client_secret="xfPIj2fqhHXlK4bz2oPToDX5E0zHZ409ZLY6ZHiU3p_jh4wv_Ycg8haUhnB6yXuA",  # noqa: E501
            )
        ],
    },
}

URLS: dict[Region, str] = {
    Region.EU: "https://prod-api.whrcloud.eu",
    Region.US: "https://api.whrcloud.com",
}


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
    def client_credentials(self) -> list[BackendConfig]:
        return CREDENTIALS[self._region][self._brand]

    @property
    def oauth_token_url(self) -> str:
        return f"{self.base_url}/oauth/token"

    @property
    def websocket_url(self) -> str:
        return f"{self.base_url}/api/v1/client_auth/webSocketUrl"

    @property
    def appliance_command_url(self) -> str:
        return f"{self.base_url}/api/v1/appliance/command"

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
