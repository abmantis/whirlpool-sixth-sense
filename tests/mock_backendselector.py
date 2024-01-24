from enum import Enum


class DummyBrand(Enum):
    DUMMY_BRAND = "dummy_brand"


class DummyRegion(Enum):
    DUMMY_REGION = "dummy_region"


class BackendSelectorMock:
    @property
    def brand(self):
        return DummyBrand.DUMMY_BRAND

    @property
    def region(self):
        return DummyRegion.DUMMY_REGION

    @property
    def base_url(self):
        return "http://dummy_base_url.com"

    @property
    def client_credentials(self) -> list[dict[str, str]]:
        return [
            {
                "client_id": "dummy_client_id",
                "client_secret": "dummy_client_secret",
            }
        ]
