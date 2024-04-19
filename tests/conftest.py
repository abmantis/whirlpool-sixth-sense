import aiohttp
import pytest
import pytest_asyncio
from aioresponses import aioresponses

from tests.mock_backendselector import (
    BackendSelectorMock,
    BackendSelectorMockMultipleCreds,
)
from whirlpool.auth import Auth


@pytest.fixture
def aioresponses_mock():
    with aioresponses() as m:
        yield m


@pytest.fixture(params=[BackendSelectorMock, BackendSelectorMockMultipleCreds])
def backend_selector_mock(request):
    yield request.param()


@pytest_asyncio.fixture
async def auth_mock(backend_selector_mock):
    session = aiohttp.ClientSession()
    auth = Auth(backend_selector_mock, "email", "secretpass", session)
    yield auth
    await session.close()
