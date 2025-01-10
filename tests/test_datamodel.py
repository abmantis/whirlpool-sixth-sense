import json
import logging
from pathlib import Path

from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.backendselector import BackendSelector
from whirlpool.dryer import Dryer

LOGGER = logging.getLogger(__name__)


ACCOUNT_ID = 111222333


CURR_DIR = Path(__file__).parent
DATA_DIR = CURR_DIR / "data"

DRYER_DATA = json.loads((DATA_DIR / "dryer_data.json").read_text())
MODEL_DATA = json.loads((DATA_DIR / "data_model.json").read_text())

DATA1 = DRYER_DATA["DATA1"]


async def test_data_model(
    dryer: Dryer,
    backend_selector_mock: BackendSelector,
    aioresponses_mock,
    appliances_manager: AppliancesManager
):
    aioresponses_mock.get(
        backend_selector_mock.ws_url,
        payload={"url": "wss://something"},
        repeat=True,
    )
    aioresponses_mock.get(
        backend_selector_mock.get_appliance_data_url(dryer.said), payload=DATA1
    )
    aioresponses_mock.post(
        backend_selector_mock.get_data_model_url, payload=MODEL_DATA
    )

    assert dryer.data_model is None
    assert dryer.data_attrs is None

    await dryer.fetch_data()
    await dryer.fetch_data_model()

    assert dryer.data_model is not None
    assert dryer.get_enum("DryCavity_CycleSetCycleSelect") == "DryCycleTimedDry"
    assert len(dryer.get_enum_values("DryCavity_CycleSetCycleSelect")) == 10
    assert type(dryer.get_int("DryCavity_CycleSetManualDryTime")) is int
    assert dryer.get_int("DryCavity_CycleSetManualDryTime") == 1800
    assert dryer.get_int("MAC_Address") is None
    assert dryer.get_enum("Dummy") is None

    assert dryer.data_attrs is not None
    assert "DryCavity_CycleSetManualDryTime" in dryer.data_attrs
    assert "DataType" in dryer.data_attrs["DryCavity_CycleSetManualDryTime"]

