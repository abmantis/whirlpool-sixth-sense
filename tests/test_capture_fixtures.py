import argparse
from types import SimpleNamespace

import pytest

from tools import capture_fixtures


def _make_appliance(
    *,
    said: str = "WPR1XYZABC123",
    name: str = "Test Appliance",
    category: str = "fabriccare",
    model_number: str = "MODEL123",
    serial_number: str = "SERIAL123",
    raw_data: dict | None = None,
) -> SimpleNamespace:
    appliance_info = SimpleNamespace(
        category=category,
        model_number=model_number,
        serial_number=serial_number,
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


def test_capture_one_writes_utf8_json_with_canonical_category(tmp_path) -> None:
    appliance = _make_appliance(
        name="Laundry Δevice",
        raw_data={"SAID": {"value": "WPR1XYZABC123", "updateTime": 123}},
    )

    capture_fixtures._capture_one(appliance, tmp_path, redact=False)

    suffix = capture_fixtures._fixture_suffix(
        appliance.appliance_info.model_number, appliance.said
    )
    thing_path = tmp_path / f"thing_simplenamespace_{suffix}.json"
    state_path = tmp_path / f"state_simplenamespace_{suffix}_full.json"

    assert thing_path.read_bytes().endswith(b"\n")
    assert state_path.read_bytes().endswith(b"\n")

    thing_data = thing_path.read_text(encoding="utf-8")
    state_data = state_path.read_text(encoding="utf-8")
    assert '"Category": "FabricCare"' in thing_data
    assert '"value": "WPR1XYZABC123"' in state_data


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
            self.all_appliances = {
                "ok": _make_appliance(said="ok"),
                "bad": _make_appliance(said="bad"),
            }
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
    monkeypatch.setattr(capture_fixtures, "AwsAppliancesManager", DummyManager)
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
