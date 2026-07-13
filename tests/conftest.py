import json
from collections.abc import AsyncGenerator
from http import HTTPStatus

import aiohttp
import pytest
import pytest_asyncio
from aiointercept import aiointercept

from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.auth import Auth
from whirlpool.backendselector import BackendSelector
from whirlpool.types import Brand, Region

from . import ACCOUNT_ID, DATA_DIR


@pytest_asyncio.fixture
async def aiointercept_mock() -> AsyncGenerator[aiointercept]:
    async with aiointercept(mock_external_urls=True) as m:
        yield m


@pytest_asyncio.fixture
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
    aiointercept_mock: aiointercept,
) -> AsyncGenerator[AppliancesManager]:
    with open(DATA_DIR / "owned_appliances.json") as f:
        owned_appliance_data = json.load(f)

    with open(DATA_DIR / "shared_appliances.json") as f:
        shared_appliance_data = json.load(f)

    with open(DATA_DIR / "mock_data.json") as f:
        mock_data = json.load(f)

    # The shared fixture only mocks the HTTP API; the AWS IoT path is expected
    # to be absent, so let its token renewal fail and connect() degrade
    # gracefully ("No AWS IoT connection. This is expected on some accounts.").
    aiointercept_mock.post(
        backend_selector.oauth_token_url,
        status=HTTPStatus.BAD_REQUEST,
        repeat=True,
    )

    aiointercept_mock.get(
        backend_selector.user_details_url,
        payload={"accountId": ACCOUNT_ID},
        repeat=True,
    )
    aiointercept_mock.get(
        backend_selector.get_owned_appliances_url(ACCOUNT_ID),
        payload={ACCOUNT_ID: owned_appliance_data},
        repeat=True,
    )
    aiointercept_mock.get(
        backend_selector.shared_appliances_url,
        payload=shared_appliance_data,
        repeat=True,
    )

    aiointercept_mock.get(
        backend_selector.websocket_url,
        payload={"url": "wss://something"},
        repeat=True,
    )

    # Pre-set data URL mocks for all known SAIDs before connect(),
    # since connect() now internally fetches appliances.
    for said, data in mock_data.items():
        aiointercept_mock.get(
            backend_selector.get_appliance_data_url(said),
            payload=data,
        )

    appliances_manager = AppliancesManager(
        backend_selector, auth, client_session_fixture
    )
    await appliances_manager.connect()
    yield appliances_manager
    await appliances_manager.disconnect()
