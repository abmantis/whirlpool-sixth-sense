import argparse
import json
from types import SimpleNamespace

import aiohttp
import pytest

from tools import capture_fixtures
from whirlpool.auth import Auth
from whirlpool.backendselector import BackendSelector
from whirlpool.httpapi.appliance import Appliance as HttpAppliance
from whirlpool.types import ApplianceInfo


def _make_appliance(
    *,
    said: str = "WPR1XYZABC123",
    name: str = "Test Appliance",
    category: str = "fabriccare",
    model_number: str = "MODEL123",
    serial_number: str = "SERIAL123",
    raw_info: dict | None = None,
    raw_data: dict | None = None,
) -> SimpleNamespace:
    appliance_info = SimpleNamespace(
        category=category,
        model_number=model_number,
        serial_number=serial_number,
        raw_info=raw_info or {},
    )
    return SimpleNamespace(
        said=said,
        name=name,
        appliance_info=appliance_info,
        get_raw_data=lambda: raw_data or {},
    )


def test_redact_preserves_nested_identifier_structure() -> None:
    redacted = capture_fixtures._redact(
        {
            "thingName": "WPR1XYZABC123",
            "SAID": {"value": "WPR1XYZABC123", "updateTime": 123},
            "serialNumber": "SERIAL123",
            "WifiMacAddress": ["aa:bb:cc:dd:ee:ff"],
            "nested": {"said": "WPR1XYZABC123"},
        },
        "WPR1XYZABC123",
    )

    token = capture_fixtures._said_token("WPR1XYZABC123")
    assert redacted["thingName"] == token
    assert redacted["SAID"] == {"value": token, "updateTime": 123}
    assert redacted["serialNumber"] == "REDACTED"
    assert redacted["WifiMacAddress"] == ["REDACTED"]
    assert redacted["nested"]["said"] == token


def test_capture_one_writes_awsiot_fixtures(tmp_path) -> None:
    thing = {
        "thingName": "WPR1XYZABC123",
        "thingTypeName": "MODEL123",
        "attributes": {"Category": "FabricCare", "CapabilityPartNumber": "W1"},
    }
    appliance = _make_appliance(
        raw_info=thing,
        raw_data={"SAID": {"value": "WPR1XYZABC123", "updateTime": 123}},
    )

    capture_fixtures._capture_one(appliance, tmp_path, redact=False)

    suffix = capture_fixtures._fixture_suffix(
        appliance.appliance_info.model_number, appliance.said
    )
    thing_path = tmp_path / "awsiot" / f"thing_simplenamespace_{suffix}.json"
    state_path = tmp_path / "awsiot" / f"state_simplenamespace_{suffix}_full.json"

    assert thing_path.read_bytes().endswith(b"\n")
    assert state_path.read_bytes().endswith(b"\n")

    assert json.loads(thing_path.read_text(encoding="utf-8")) == thing
    state_data = state_path.read_text(encoding="utf-8")
    assert '"value": "WPR1XYZABC123"' in state_data


async def test_capture_one_writes_redacted_httpapi_fixtures(
    tmp_path,
    backend_selector: BackendSelector,
    auth: Auth,
    client_session_fixture: aiohttp.ClientSession,
) -> None:
    said = "WPR1XYZABC123"
    record = {"SAID": said, "SERIAL": "SERIAL123", "DATA_MODEL_KEY": "DDM_X"}
    appliance = HttpAppliance(
        backend_selector,
        auth,
        client_session_fixture,
        ApplianceInfo(said, "Unsupported", "cooking", "MODEL123", "SERIAL123", record),
    )
    appliance._data_dict = {
        "_id": said,
        "applianceId": said,
        "attributes": {
            "MAC_Address": {"value": "aa:bb:cc:dd:ee:ff", "updateTime": 123},
            "Online": {"value": "1", "updateTime": 123},
        },
    }

    capture_fixtures._capture_one(appliance, tmp_path, redact=True)

    suffix = capture_fixtures._fixture_suffix("MODEL123", said)
    appliance_data = json.loads(
        (tmp_path / "httpapi" / f"appliance_unsupported_{suffix}.json").read_text()
    )
    data = json.loads(
        (tmp_path / "httpapi" / f"data_unsupported_{suffix}.json").read_text()
    )

    token = capture_fixtures._said_token(said)
    assert appliance_data == {
        "SAID": token,
        "SERIAL": "REDACTED",
        "DATA_MODEL_KEY": "DDM_X",
    }
    assert data["_id"] == token
    assert data["applianceId"] == token
    assert data["attributes"]["MAC_Address"]["value"] == "REDACTED"
    assert data["attributes"]["Online"]["value"] == "1"


@pytest.mark.asyncio
async def test_amain_returns_nonzero_when_any_capture_fails(
    tmp_path, monkeypatch
) -> None:
    class DummySession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class DummyAuth:
        def __init__(self, *_args):
            pass

        async def do_auth(self):
            return None

    class DummyManager:
        last_instance = None

        def __init__(self, *_args):
            self.__class__.last_instance = self
            self.aircons = []
            self.dryers = []
            self.washers = []
            self.ovens = []
            self.microwaves = []
            self.refrigerators = []
            self.unsupported_appliances = [
                _make_appliance(said="ok"),
                _make_appliance(said="bad"),
            ]
            self.disconnected = False

        async def connect(self) -> bool:
            return True

        async def disconnect(self):
            self.disconnected = True

    def fake_capture_one(appliance, *_args, **_kwargs):
        if appliance.said == "bad":
            raise RuntimeError("boom")

    monkeypatch.setattr(capture_fixtures.aiohttp, "ClientSession", DummySession)
    monkeypatch.setattr(capture_fixtures, "Auth", DummyAuth)
    monkeypatch.setattr(capture_fixtures, "AppliancesManager", DummyManager)
    monkeypatch.setattr(capture_fixtures, "BackendSelector", lambda *_args: object())
    monkeypatch.setattr(capture_fixtures, "_capture_one", fake_capture_one)

    args = argparse.Namespace(
        verbose=False,
        brand="KitchenAid",
        region="US",
        list_only=False,
        capture_all=True,
        said=None,
        output_dir=tmp_path,
        redact=False,
        email="user@example.com",
        password="secret",
    )

    result = await capture_fixtures._amain(args)

    assert result == 5
    assert DummyManager.last_instance is not None
    assert DummyManager.last_instance.disconnected is True
