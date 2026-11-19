import argparse
import json
import logging
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

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


@pytest.mark.parametrize("name", ["Private Household", b"Private Household".hex()])
def test_redact_aws_name_and_laundry_session(name: str) -> None:
    data = {"attributes": {"Name": name}, "washer": {"sessionId": "private-session"}}
    result = capture_fixtures._redact(data, "TEST_SAID")
    assert result == {
        "attributes": {"Name": "REDACTED"},
        "washer": {"sessionId": "REDACTED"},
    }


def test_redact_sensitive_nested_containers() -> None:
    data = {
        "Serial": {"nested": [{"raw": "private-serial"}], "updateTime": 123},
        "WifiMacAddress": [{"raw": "private-mac"}],
    }
    result = capture_fixtures._redact(data, "TEST_SAID")
    assert result == {
        "Serial": {"nested": [{"raw": "REDACTED"}], "updateTime": 123},
        "WifiMacAddress": [{"raw": "REDACTED"}],
    }


def test_redact_embedded_said_in_strings_and_keys() -> None:
    said = "TEST_SAID"
    result = capture_fixtures._redact(
        {f"dt/MODEL/{said}/state": [f"cmd/MODEL/{said}/request/client"]}, said
    )
    token = capture_fixtures._said_token(said)
    assert result == {f"dt/MODEL/{token}/state": [f"cmd/MODEL/{token}/request/client"]}
    assert said not in json.dumps(result)


def test_redacted_capture_logs_do_not_disclose_names_or_local_paths(
    tmp_path, caplog: pytest.LogCaptureFixture
) -> None:
    appliance = _make_appliance(name="Private Household", said="TEST_SAID")
    caplog.set_level(logging.INFO, logger=capture_fixtures.LOGGER.name)
    capture_fixtures._capture_one(appliance, tmp_path, redact=True)
    assert "TEST_SAID" not in caplog.text
    assert "Private Household" not in caplog.text
    assert str(tmp_path) not in caplog.text
    assert capture_fixtures._said_token("TEST_SAID") in caplog.text


@pytest.mark.parametrize("redact", [True, False])
def test_list_respects_redaction(redact: bool, capsys: pytest.CaptureFixture) -> None:
    manager = MagicMock(
        spec=capture_fixtures.AppliancesManager,
        aircons=[],
        dryers=[],
        washers=[],
        ovens=[],
        microwaves=[],
        refrigerators=[],
        unsupported_appliances=[
            _make_appliance(said="TEST_SAID", name="Private Household")
        ],
    )
    args = argparse.Namespace(list_only=True, redact=redact)
    assert capture_fixtures._capture(args, manager) == 0
    output = capsys.readouterr().out
    assert ("TEST_SAID" in output) is not redact
    assert ("Private Household" in output) is not redact


def test_redacted_failure_does_not_log_exception_payload(
    tmp_path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    manager = MagicMock(
        spec=capture_fixtures.AppliancesManager,
        aircons=[],
        dryers=[],
        washers=[],
        ovens=[],
        microwaves=[],
        refrigerators=[],
        unsupported_appliances=[
            _make_appliance(said="TEST_SAID", name="Private Household")
        ],
    )
    args = argparse.Namespace(
        list_only=False, redact=True, capture_all=True, said=None, output_dir=tmp_path
    )

    def fail(*_args, **_kwargs):
        raise RuntimeError("PRIVATE_TOKEN TEST_SAID Private Household")

    monkeypatch.setattr(capture_fixtures, "_capture_one", fail)
    assert capture_fixtures._capture(args, manager) == 5
    assert "PRIVATE_TOKEN" not in caplog.text
    assert "TEST_SAID" not in caplog.text
    assert "Private Household" not in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


def _capture_argv() -> list[str]:
    return [
        "capture_fixtures",
        "--email",
        "user@example.com",
        "--brand",
        "Whirlpool",
        "--region",
        "US",
        "--all",
    ]


def test_missing_password_uses_hidden_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", _capture_argv())
    monkeypatch.setattr(
        capture_fixtures.getpass, "getpass", lambda _prompt: "test-secret"
    )
    args = capture_fixtures._parse_args()
    assert args.password == "test-secret"


def test_explicit_password_does_not_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", [*_capture_argv(), "--password", "test-secret"])
    monkeypatch.setattr(
        capture_fixtures.getpass, "getpass", lambda _prompt: pytest.fail("prompted")
    )
    assert capture_fixtures._parse_args().password == "test-secret"


def test_nonhidden_fallback_is_rejected_before_reading(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    import warnings

    def unsafe_prompt(_prompt):
        warnings.warn(
            "Echo unavailable", capture_fixtures.getpass.GetPassWarning, stacklevel=2
        )
        pytest.fail("Must not continue to echoing input")

    monkeypatch.setattr(sys, "argv", _capture_argv())
    monkeypatch.setattr(capture_fixtures.getpass, "getpass", unsafe_prompt)
    with pytest.raises(SystemExit) as exc:
        capture_fixtures._parse_args()
    assert exc.value.code == 2
    assert "hidden password input is required" in capsys.readouterr().err


def test_redact_said_in_sensitive_subtree_keys() -> None:
    data = {"Serial": {"reference/TEST_SAID": [{"path/TEST_SAID": "private"}]}}
    result = capture_fixtures._redact(data, "TEST_SAID")
    token = capture_fixtures._said_token("TEST_SAID")
    assert result == {"Serial": {f"reference/{token}": [{f"path/{token}": "REDACTED"}]}}
    assert "TEST_SAID" not in json.dumps(result)


@pytest.mark.parametrize("stage", ["authentication", "connection", "disconnect"])
def test_redacted_cli_failure_suppresses_provider_payload(
    stage: str, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(
        capture_fixtures, "_parse_args", lambda: argparse.Namespace(redact=True)
    )

    async def fail(_args):
        raise RuntimeError(f"PRIVATE_PROVIDER_TOKEN {stage}")

    monkeypatch.setattr(capture_fixtures, "_amain", fail)
    with pytest.raises(SystemExit) as exc:
        capture_fixtures.main()
    assert exc.value.code == 1
    assert "PRIVATE_PROVIDER_TOKEN" not in caplog.text
    assert all(record.exc_info is None for record in caplog.records)


def test_unredacted_cli_retains_diagnostic_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        capture_fixtures, "_parse_args", lambda: argparse.Namespace(redact=False)
    )

    async def fail(_args):
        raise RuntimeError("synthetic diagnostic")

    monkeypatch.setattr(capture_fixtures, "_amain", fail)
    with pytest.raises(RuntimeError, match="synthetic diagnostic"):
        capture_fixtures.main()
