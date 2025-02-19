import json

import aiohttp
import pytest
import pytest_asyncio
from aioresponses import aioresponses

from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.auth import Auth

from . import ACCOUNT_ID, DATA_DIR
from .mock_backendselector import (
    BackendSelectorMock,
    BackendSelectorMockMultipleCreds,
)


@pytest.fixture
def aioresponses_mock():
    with aioresponses() as m:
        yield m


@pytest_asyncio.fixture(scope="session")
async def client_session_fixture():
    session = aiohttp.ClientSession()
    yield session
    await session.close()


@pytest.fixture(params=[BackendSelectorMock, BackendSelectorMockMultipleCreds])
def backend_selector_mock(request):
    yield request.param()


@pytest.fixture(name="auth")
def auth_fixture(backend_selector_mock, client_session_fixture):
    auth = Auth(backend_selector_mock, "email", "secretpass", client_session_fixture)
    yield auth


@pytest.fixture(name="appliances_manager")
async def appliances_manager_fixture(
    backend_selector_mock, auth, client_session_fixture, aioresponses_mock
):
    with open(DATA_DIR / "owned_appliances.json") as f:
        owned_appliance_data = json.load(f)

    with open(DATA_DIR / "shared_appliances.json") as f:
        shared_appliance_data = json.load(f)

    with open(DATA_DIR / "mock_data.json") as f:
        mock_data = json.load(f)

    aioresponses_mock.get(
        backend_selector_mock.user_details_url, payload={"accountId": ACCOUNT_ID}
    )
    aioresponses_mock.get(
        backend_selector_mock.get_owned_appliances_url(ACCOUNT_ID),
        payload={ACCOUNT_ID: owned_appliance_data},
    )
    aioresponses_mock.get(
        backend_selector_mock.shared_appliances_url, payload=shared_appliance_data
    )

    aioresponses_mock.get(
        backend_selector_mock.websocket_url,
        payload={"url": "wss://something"},
        repeat=True,
    )

    appliances_manager = AppliancesManager(
        backend_selector_mock, auth, client_session_fixture
    )
    await appliances_manager.fetch_appliances()

    for said in appliances_manager.all_appliances.keys():
        aioresponses_mock.get(
            backend_selector_mock.get_appliance_data_url(said),
            payload=mock_data[said],
        )

    await appliances_manager.connect()
    yield appliances_manager
    await appliances_manager.disconnect()
