import pytest
from aioresponses import aioresponses

from tests import ACCOUNT_ID
from whirlpool.auth import Auth
from whirlpool.backendselector import BackendSelector


@pytest.mark.usefixtures("appliances_manager")
async def test_fetch_appliances_calls_owned_and_shared_methods(
    auth: Auth,
    backend_selector: BackendSelector,
    aioresponses_mock: aioresponses,
):
    headers = auth.create_headers()
    shared_headers = {**headers, "WP-CLIENT-BRAND": backend_selector.brand.name}

    aioresponses_mock.assert_called_with(
        backend_selector.get_owned_appliances_url(ACCOUNT_ID),
        "GET",
        headers=headers,
    )

    aioresponses_mock.assert_called_with(
        backend_selector.shared_appliances_url, "GET", headers=shared_headers
    )
