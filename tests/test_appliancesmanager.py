from unittest.mock import MagicMock

import pytest

from tests import ACCOUNT_ID


@pytest.mark.usefixtures("appliances_manager")
async def test_fetch_appliances_calls_owned_and_shared_methods(
    auth: MagicMock,
    backend_selector_mock: MagicMock,
    aioresponses_mock: MagicMock,
):
    headers = auth.create_headers()
    shared_headers = {**headers, "WP-CLIENT-BRAND": backend_selector_mock.brand.name}

    aioresponses_mock.assert_called_with(
        backend_selector_mock.get_owned_appliances_url(ACCOUNT_ID),
        "GET",
        headers=headers,
    )

    aioresponses_mock.assert_called_with(
        backend_selector_mock.shared_appliances_url, "GET", headers=shared_headers
    )
