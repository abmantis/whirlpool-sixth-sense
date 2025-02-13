from enum import Enum

from whirlpool import types
from whirlpool.backendselector import BackendSelector


class DummyBrand(Enum):
    DUMMY_BRAND = "dummy_brand"


class DummyRegion(Enum):
    DUMMY_REGION = "dummy_region"


class BackendSelectorMock(BackendSelector):
    def __init__(self):
        super().__init__(types.Brand.Whirlpool, types.Region.EU)

    @property
    def base_url(self):
        return "http://dummy_base_url.com"

    @property
    def client_credentials(self) -> list[dict[str, str]]:
        return [
            {
                "client_id": "dummy_client_id1",
                "client_secret": "dummy_client_secret1",
            },
        ]


class BackendSelectorMockMultipleCreds(BackendSelectorMock):
    @property
    def client_credentials(self) -> list[dict[str, str]]:
        return [
            {
                "client_id": "dummy_client_id1",
                "client_secret": "dummy_client_secret1",
            },
            {
                "client_id": "dummy_client_id2",
                "client_secret": "dummy_client_secret2",
            },
        ]
