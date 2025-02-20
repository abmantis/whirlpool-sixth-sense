import json
from collections.abc import AsyncGenerator, Generator

import aiohttp
import pytest
import pytest_asyncio
from aioresponses import aioresponses

from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.auth import Auth
from whirlpool.backendselector import BackendSelector
from whirlpool.types import Brand, Region

from . import ACCOUNT_ID, DATA_DIR


@pytest.fixture
def aioresponses_mock() -> Generator[aioresponses]:
    with aioresponses() as m:
        yield m


@pytest_asyncio.fixture(scope="session")
async def client_session_fixture() -> AsyncGenerator[aiohttp.ClientSession]:
    session = aiohttp.ClientSession()
    yield session
    await session.close()


@pytest.fixture(name="backend_selector")
def backen_selector_fixture() -> BackendSelector:
    return BackendSelector(Brand.Whirlpool, Region.EU)


@pytest.fixture(name="auth")
def auth_fixture(
    backend_selector: BackendSelector, client_session_fixture: aiohttp.ClientSession
) -> Auth:
    return Auth(backend_selector, "email", "secretpass", client_session_fixture)


@pytest.fixture(name="appliances_manager")
async def appliances_manager_fixture(
    auth: Auth,
    backend_selector: BackendSelector,
    client_session_fixture: aiohttp.ClientSession,
    aioresponses_mock: aioresponses,
) -> AsyncGenerator[AppliancesManager]:
    with open(DATA_DIR / "owned_appliances.json") as f:
        owned_appliance_data = json.load(f)

    with open(DATA_DIR / "shared_appliances.json") as f:
        shared_appliance_data = json.load(f)

    with open(DATA_DIR / "mock_data.json") as f:
        mock_data = json.load(f)

    aioresponses_mock.get(
        backend_selector.user_details_url, payload={"accountId": ACCOUNT_ID}
    )
    aioresponses_mock.get(
        backend_selector.get_owned_appliances_url(ACCOUNT_ID),
        payload={ACCOUNT_ID: owned_appliance_data},
    )
    aioresponses_mock.get(
        backend_selector.shared_appliances_url, payload=shared_appliance_data
    )

    aioresponses_mock.get(
        backend_selector.websocket_url,
        payload={"url": "wss://something"},
        repeat=True,
    )

    appliances_manager = AppliancesManager(
        backend_selector, auth, client_session_fixture
    )
    await appliances_manager.fetch_appliances()

    for said in appliances_manager.all_appliances.keys():
        aioresponses_mock.get(
            backend_selector.get_appliance_data_url(said),
            payload=mock_data[said],
        )
    await appliances_manager.connect()
    yield appliances_manager
    await appliances_manager.disconnect()
