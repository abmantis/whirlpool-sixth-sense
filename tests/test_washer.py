import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from yarl import URL

from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.backendselector import BackendSelector
from whirlpool.washer import Washer, MachineState

ACCOUNT_ID = 111222333


CURR_DIR = Path(__file__).parent
DATA_DIR = CURR_DIR / "data"

WASHER_DATA = json.loads((DATA_DIR / "washer_data.json").read_text())

DATA1 = WASHER_DATA["DATA1"]


async def test_attributes(
    washer: Washer, backend_selector_mock: BackendSelector, aioresponses_mock, appliances_manager
):
    aioresponses_mock.get(
        backend_selector_mock.ws_url,
        payload={"url": "wss://something"},
        repeat=True,
    )
    aioresponses_mock.get(
        backend_selector_mock.get_appliance_data_url(washer.said), payload=DATA1
    )

    await washer.fetch_data()

    await appliances_manager.connect()
    assert washer.get_machine_state() == MachineState.Standby
    assert washer.get_cycle_status_sensing() == 0
    assert washer.get_cycle_status_filling() == 0
    assert washer.get_cycle_status_soaking() == 0
    assert washer.get_cycle_status_washing() == 0
    assert washer.get_cycle_status_rinsing() == 0
    assert washer.get_cycle_status_spinning() == 0
    await appliances_manager.disconnect()

