from unittest.mock import AsyncMock, Mock

import pytest


@pytest.fixture(name="aio_httpclient")
def fixture_aio_httpclient(mocker):
    """Set up aiohttp ClientSession fixture."""

    http_client = mocker.patch("aiohttp.ClientSession").return_value
    http_client.get = Mock()
    http_client.post = Mock()
    http_client.close = AsyncMock()
    return http_client
