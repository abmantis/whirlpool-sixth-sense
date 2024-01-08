class BackendSelectorMock:
    @property
    def brand(self):
        return "dummy_brand"

    @property
    def region(self):
        return "dummy_region"

    @property
    def base_url(self):
        return "http://dummy_base_url.com"

    @property
    def credentials(self) -> list[dict[str, str]]:
        return [
            {
                "client_id": "dummy_client_id",
                "client_secret": "dummy_client_secret",
            }
        ]
