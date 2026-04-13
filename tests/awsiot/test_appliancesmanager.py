import copy
from typing import Any
from unittest.mock import patch

import pytest

from whirlpool_aws.awsiot.appliancesmanager import AppliancesManager
from whirlpool_aws.awsiot.capabilities import (
    CapabilityProfile,
    parse_capability_profile,
)
from whirlpool_aws.microwave import Microwave as MicrowaveABC


class _FakeWhirlpoolAuth:
    async def get_access_token(self) -> str | None:
        return "token"


@pytest.fixture
def patched_manager(
    fake_mqtt, capability_mwo_raw, thing_mwo, state_mwo_full
):
    """Patch AppliancesManager's MQTT client, Things, and downloader."""

    things_return: list[dict[str, Any]] = [thing_mwo]

    class _FakeThings:
        def __init__(self, *args, **kwargs):
            pass

        async def list_things(self) -> list[dict[str, Any]]:
            return list(things_return)

    async def fake_download(
        self, said: str, model: str, part: str
    ) -> CapabilityProfile:
        return parse_capability_profile(capability_mwo_raw)

    async def fake_fetch_data(self) -> bool:
        # Seed state directly, skipping MQTT round-trip.
        self._state = copy.deepcopy(state_mwo_full)
        self._initial_state_event.set()
        return True

    with (
        patch("whirlpool_aws.awsiot.appliancesmanager.Things", _FakeThings),
        patch(
            "whirlpool_aws.awsiot.appliancesmanager.MqttClient",
            return_value=fake_mqtt,
        ),
        patch(
            "whirlpool_aws.awsiot.capabilities.CapabilityDownloader.get",
            fake_download,
        ),
        patch(
            "whirlpool_aws.awsiot.appliance.Appliance.fetch_data",
            fake_fetch_data,
        ),
    ):
        yield things_return


async def test_connect_registers_microwave(
    patched_manager, fake_mqtt, client_session_fixture
):
    # Ensure Microwave registration is loaded before factory build.
    import whirlpool_aws.awsiot.microwave  # noqa: F401

    manager = AppliancesManager(
        _FakeWhirlpoolAuth(), client_session_fixture, lambda: None  # type: ignore[arg-type]
    )
    ok = await manager.connect()
    assert ok is True
    assert len(manager.microwaves) == 1
    assert isinstance(manager.microwaves[0], MicrowaveABC)


async def test_connect_with_empty_things_still_succeeds(
    patched_manager, client_session_fixture
):
    patched_manager.clear()
    manager = AppliancesManager(
        _FakeWhirlpoolAuth(), client_session_fixture, lambda: None  # type: ignore[arg-type]
    )
    ok = await manager.connect()
    assert ok is True
    assert manager.microwaves == []


async def test_thing_without_capability_part_number_is_skipped(
    patched_manager, client_session_fixture, thing_mwo
):
    broken = dict(thing_mwo)
    broken["attributes"] = dict(thing_mwo["attributes"])
    broken["attributes"].pop("CapabilityPartNumber")
    patched_manager.clear()
    patched_manager.append(broken)

    manager = AppliancesManager(
        _FakeWhirlpoolAuth(), client_session_fixture, lambda: None  # type: ignore[arg-type]
    )
    ok = await manager.connect()
    assert ok is True
    assert manager.microwaves == []


async def test_one_failing_appliance_does_not_abort_others(
    patched_manager, client_session_fixture, thing_mwo, capability_mwo_raw
):
    import whirlpool_aws.awsiot.microwave  # noqa: F401
    from whirlpool_aws.awsiot.capabilities import (
        CapabilityDownloadError,
        parse_capability_profile,
    )

    second = dict(thing_mwo)
    second["thingName"] = "SECOND"
    patched_manager.append(second)

    calls: list[str] = []

    async def selective_download(
        self, said: str, model: str, part: str
    ) -> CapabilityProfile:
        calls.append(said)
        if said == thing_mwo["thingName"]:
            raise CapabilityDownloadError("boom")
        return parse_capability_profile(capability_mwo_raw)

    with patch(
        "whirlpool_aws.awsiot.capabilities.CapabilityDownloader.get",
        selective_download,
    ):
        manager = AppliancesManager(
            _FakeWhirlpoolAuth(), client_session_fixture, lambda: None  # type: ignore[arg-type]
        )
        ok = await manager.connect()
    assert ok is True
    # Second one should have been registered despite the first's failure.
    assert any(m.said == "SECOND" for m in manager.microwaves)


async def test_connect_disconnects_mqtt_on_list_things_failure(
    patched_manager, fake_mqtt, client_session_fixture
):
    from whirlpool_aws.awsiot.auth import AuthException

    class _FailingThings:
        def __init__(self, *args, **kwargs):
            pass

        async def list_things(self) -> list[dict[str, Any]]:
            raise AuthException("Auth token expired")

    manager = AppliancesManager(
        _FakeWhirlpoolAuth(), client_session_fixture, lambda: None  # type: ignore[arg-type]
    )
    with patch("whirlpool_aws.awsiot.appliancesmanager.Things", _FailingThings):
        ok = await manager.connect()

    assert ok is False
    assert not fake_mqtt.is_connected()
