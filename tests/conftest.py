import json
from collections.abc import AsyncGenerator

import aiohttp
import pytest
import pytest_asyncio
from aiointercept import aiointercept

from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.auth import Auth
from whirlpool.backendselector import BackendSelector
from whirlpool.types import Brand, Region

from . import ACCOUNT_ID, DATA_DIR
from .awsiot.mocks import (
    MWO_CAP_PART,
    MWO_CAPABILITY_PROFILE,
    THING,
    FakePahoBroker,
    mock_aws_api,
)


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


@pytest.fixture
def http_api_mock(
    backend_selector: BackendSelector, aiointercept_mock: aiointercept
) -> aiointercept:
    """Mock the HTTP API at the wire, serving the appliances in `tests/data`."""
    with open(DATA_DIR / "owned_appliances.json") as f:
        owned_appliance_data = json.load(f)

    with open(DATA_DIR / "shared_appliances.json") as f:
        shared_appliance_data = json.load(f)

    with open(DATA_DIR / "mock_data.json") as f:
        mock_data = json.load(f)

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

    return aiointercept_mock


@pytest.fixture
def fake_paho_broker(monkeypatch: pytest.MonkeyPatch) -> FakePahoBroker:
    """Replace paho's MQTT client with a fake broker; nothing is preloaded."""
    broker = FakePahoBroker()
    monkeypatch.setattr("whirlpool.awsiot.mqttclient.mqtt.Client", broker)
    return broker


@pytest.fixture
def aws_api_mock(
    backend_selector: BackendSelector,
    aiointercept_mock: aiointercept,
    fake_paho_broker: FakePahoBroker,
) -> FakePahoBroker:
    """Mock the AWS IoT API, serving the microwave in `tests/data/awsiot`."""
    mock_aws_api(
        aiointercept_mock,
        backend_selector,
        fake_paho_broker,
        [THING],
        {MWO_CAP_PART: MWO_CAPABILITY_PROFILE},
    )
    return fake_paho_broker


@pytest.fixture(name="appliances_manager")
async def appliances_manager_fixture(
    auth: Auth,
    backend_selector: BackendSelector,
    client_session_fixture: aiohttp.ClientSession,
    http_api_mock: aiointercept,
    aws_api_mock: FakePahoBroker,
) -> AsyncGenerator[AppliancesManager]:
    """A manager connected to both the HTTP API and AWS IoT."""
    assert await auth.do_auth()
    appliances_manager = AppliancesManager(
        backend_selector, auth, client_session_fixture
    )
    await appliances_manager.connect()
    yield appliances_manager
    await appliances_manager.disconnect()
