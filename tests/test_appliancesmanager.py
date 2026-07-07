import asyncio

import pytest
from aioresponses import aioresponses
from yarl import URL

from tests import ACCOUNT_ID
from whirlpool import appliancesmanager
from whirlpool.appliancesmanager import AppliancesManager
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


def _get_request_count(aioresponses_mock: aioresponses, url: str) -> int:
    return len(aioresponses_mock.requests.get(("GET", URL(url)), []))


async def test_keepalive_periodically_fetches_an_appliance(
    appliances_manager: AppliancesManager,
    backend_selector: BackendSelector,
    aioresponses_mock: aioresponses,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(appliancesmanager, "KEEPALIVE_INTERVAL_SECONDS", 0.01)

    for said in appliances_manager.all_appliances:
        aioresponses_mock.get(
            backend_selector.get_appliance_data_url(said), payload={}, repeat=True
        )
    kept_alive_url = backend_selector.get_appliance_data_url(
        next(iter(appliances_manager.all_appliances))
    )

    # Restart the listener so the patched keepalive interval takes effect.
    await appliances_manager.stop_event_listener()
    await appliances_manager.start_event_listener()
    count_after_start = _get_request_count(aioresponses_mock, kept_alive_url)

    await asyncio.sleep(0.05)
    assert _get_request_count(aioresponses_mock, kept_alive_url) > count_after_start


async def test_keepalive_stops_with_event_listener(
    appliances_manager: AppliancesManager,
    backend_selector: BackendSelector,
    aioresponses_mock: aioresponses,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(appliancesmanager, "KEEPALIVE_INTERVAL_SECONDS", 0.01)

    for said in appliances_manager.all_appliances:
        aioresponses_mock.get(
            backend_selector.get_appliance_data_url(said), payload={}, repeat=True
        )
    kept_alive_url = backend_selector.get_appliance_data_url(
        next(iter(appliances_manager.all_appliances))
    )

    await appliances_manager.stop_event_listener()
    await appliances_manager.start_event_listener()
    await appliances_manager.stop_event_listener()

    count_after_stop = _get_request_count(aioresponses_mock, kept_alive_url)
    await asyncio.sleep(0.05)
    assert _get_request_count(aioresponses_mock, kept_alive_url) == count_after_stop
