from unittest.mock import patch

import aiohttp
import pytest
import pytest_asyncio
from aioresponses import aioresponses

from tests.mock_backendselector import (
    BackendSelectorMock,
    BackendSelectorMockMultipleCreds,
)
from whirlpool.aircon import Aircon
from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.auth import Auth
from whirlpool.dryer import Dryer
from whirlpool.oven import Oven
from whirlpool.refrigerator import Refrigerator
from whirlpool.types import ApplianceData
from whirlpool.washer import Washer

SAID = "WPR1XYZABC123"


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


@pytest.fixture
def auth_fixture(backend_selector_mock, client_session_fixture):
    auth = Auth(backend_selector_mock, "email", "secretpass", client_session_fixture)
    yield auth


@pytest.fixture(name="oven")
async def oven_fixture(
    backend_selector_mock, auth_fixture, client_session_fixture
):
    app_data = ApplianceData(
        said=SAID,
        name="Oven",
        data_model="RANGE_DATA_MODEL",
        category="Cooking",
        model_number="WRO1234XX1",
        serial_number="RO12345678",
    )

    with patch("whirlpool.appliance.Auth._create_headers", return_value={}):
        oven = Oven(
            backend_selector_mock, auth_fixture, client_session_fixture, app_data
        )
        yield oven


@pytest.fixture(name="aircon")
def aircon_fixture(
    backend_selector_mock, auth_fixture, client_session_fixture
):
    app_data = ApplianceData(
        said=SAID,
        name="Air Conditioner",
        data_model="AIRCON_DATA_MODEL",
        category="Climate",
        model_number="WAC1234XX1",
        serial_number="AC12345678",
    )

    with patch("whirlpool.appliance.Auth._create_headers", return_value={}):
        aircon = Aircon(
            backend_selector_mock, auth_fixture, client_session_fixture, app_data
        )
        yield aircon


@pytest.fixture(name="dryer")
def dryer_fixture(
    backend_selector_mock, auth_fixture, client_session_fixture
):
    app_data = ApplianceData(
        said=SAID,
        name="Dryer",
        data_model="DRYER_DATA_MODEL",
        category="FabricCare",
        model_number="WDR1234XX1",
        serial_number="DR12345678",
    )

    with patch("whirlpool.auth.Auth._create_headers", return_value={}):
        dryer = Dryer(
            backend_selector_mock, auth_fixture, client_session_fixture, app_data
        )
        yield dryer


@pytest.fixture(name="refrigerator")
def refrigerator_fixture(
    backend_selector_mock, auth_fixture, client_session_fixture
):
    app_data = ApplianceData(
        said=SAID,
        name="Refrigerator",
        data_model="FRIG_DATA_MODEL",
        category="Kitchen",
        model_number="WFR1234XX1",
        serial_number="FR12345678",
    )

    with patch("whirlpool.appliance.Auth._create_headers", return_value={}):
        refrigerator = Refrigerator(
            backend_selector_mock, auth_fixture, client_session_fixture, app_data
        )
        yield refrigerator


@pytest.fixture(name="washer")
def washer_fixture(
    backend_selector_mock, auth_fixture, client_session_fixture
):
    app_data = ApplianceData(
        said=SAID,
        name="Washer",
        data_model="WASHER_DATA_MODEL",
        category="FabricCare",
        model_number="WWR1234XX1",
        serial_number="WR12345678",
    )

    with patch("whirlpool.auth.Auth._create_headers", return_value={}):
        washer = Washer(
            backend_selector_mock, auth_fixture, client_session_fixture, app_data
        )
        yield washer



@pytest.fixture(name="appliances_manager")
def appliances_manager_fixture(
    backend_selector_mock, auth_fixture, client_session_fixture
):
    yield AppliancesManager(backend_selector_mock, auth_fixture, client_session_fixture)
