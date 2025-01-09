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
from whirlpool.types import ApplianceData
from whirlpool.auth import Auth
from whirlpool.oven import Oven
from whirlpool.refrigerator import Refrigerator
from whirlpool.washerdryer import WasherDryer

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

    with patch("whirlpool.appliance.Appliance._create_headers", return_value={}):
        oven = Oven(
            backend_selector_mock, auth_fixture, client_session_fixture, app_data
        )
        yield oven


@pytest.fixture(name="washer_dryer")
def washer_dryer_fixture(
    backend_selector_mock, auth_fixture, client_session_fixture
):
    app_data = ApplianceData(
        said=SAID,
        name="Washer/Dryer AIO",
        data_model="WASHDRY_DATA_MODEL",
        category="FabricCare",
        model_number="WWD1234XX1",
        serial_number="WD12345678",
    )

    with patch("whirlpool.appliance.Appliance._create_headers", return_value={}):
        washer_dryer = WasherDryer(
            backend_selector_mock, auth_fixture, client_session_fixture, app_data
        )
        yield washer_dryer


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

    with patch("whirlpool.appliance.Appliance._create_headers", return_value={}):
        aircon = Aircon(
            backend_selector_mock, auth_fixture, client_session_fixture, app_data
        )
        yield aircon

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

    with patch("whirlpool.appliance.Appliance._create_headers", return_value={}):
        refrigerator = Refrigerator(
            backend_selector_mock, auth_fixture, client_session_fixture, app_data
        )
        yield refrigerator


@pytest.fixture(name="appliances_manager")
def appliances_manager_fixture(
    backend_selector_mock, auth_fixture, client_session_fixture
):
    yield AppliancesManager(backend_selector_mock, auth_fixture, client_session_fixture)
