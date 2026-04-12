import asyncio

import pytest

from whirlpool.awsiot.appliance import Appliance, deep_merge
from whirlpool.awsiot.capabilities import parse_capability_profile
from whirlpool.types import ApplianceInfo


class _ConcreteAppliance(Appliance):
    """Minimal subclass so tests can instantiate the ABC."""


@pytest.fixture
def profile(capability_mwo_raw):
    return parse_capability_profile(capability_mwo_raw)


@pytest.fixture
def info() -> ApplianceInfo:
    return ApplianceInfo(
        said="SAIDXYZ",
        name="Test MWO",
        category="cooking",
        model_number="KMMC5019JBS",
        serial_number="D1",
    )


@pytest.fixture
async def connected(fake_mqtt, profile, info) -> _ConcreteAppliance:
    await fake_mqtt.connect()
    app = _ConcreteAppliance(fake_mqtt, info, profile)
    await app.connect()
    return app


# --- deep_merge ----------------------------------------------------------

def test_deep_merge_nested_dicts():
    base = {"a": {"b": 1, "c": 2}}
    update = {"a": {"c": 3, "d": 4}}
    result = deep_merge(base, update)
    assert result == {"a": {"b": 1, "c": 3, "d": 4}}


def test_deep_merge_replaces_non_dict_leaf():
    base = {"a": 1}
    result = deep_merge(base, {"a": 2})
    assert result == {"a": 2}


def test_deep_merge_type_mismatch_keeps_existing_and_warns(
    caplog: pytest.LogCaptureFixture,
):
    base = {"a": {"nested": 1}}
    import logging

    with caplog.at_level(logging.WARNING, logger="whirlpool.awsiot.appliance"):
        deep_merge(base, {"a": "scalar"})
    assert base["a"] == {"nested": 1}
    assert any("type mismatch" in r.message.lower() for r in caplog.records)


# --- _get_path* ----------------------------------------------------------

def test_get_path_returns_none_for_missing(connected: _ConcreteAppliance):
    assert connected._get_path("primaryCavity.nonexistent") is None
    assert connected._get_path("nope") is None


def test_get_path_traverses_nested(connected: _ConcreteAppliance, state_mwo_full):
    connected._state = state_mwo_full
    assert connected._get_path_bool("primaryCavity.cavityLight") is False
    assert connected._get_path_str("primaryCavity.cavityState") == "idle"
    assert connected._get_path_int("primaryCavity.mwoPowerLevel") == 0
    assert connected._get_path_str("hoodFan.userFanSpeed") == "off"
    assert connected._get_path_str("hoodLight") == "med"


def test_get_path_type_coercion_none_on_mismatch(connected: _ConcreteAppliance):
    connected._state = {"x": "not-an-int"}
    assert connected._get_path_int("x") is None


# --- lifecycle -----------------------------------------------------------

async def test_connect_subscribes_expected_topics(
    fake_mqtt, profile, info
) -> None:
    await fake_mqtt.connect()
    app = _ConcreteAppliance(fake_mqtt, info, profile)
    await app.connect()
    model = info.model_number
    said = info.said
    cid = fake_mqtt.client_id
    expected = {
        f"cmd/{model}/{said}/response/{cid}",
        f"dt/{model}/{said}/state/update",
        f"$aws/events/presence/connected/{said}",
        f"$aws/events/presence/disconnected/{said}",
    }
    assert expected.issubset(fake_mqtt.subscriptions)


async def test_fetch_data_publishes_getstate_and_resolves_on_response(
    fake_mqtt, profile, info, state_mwo_full
) -> None:
    await fake_mqtt.connect()
    app = _ConcreteAppliance(fake_mqtt, info, profile)
    await app.connect()
    fake_mqtt.clear_published()

    async def fire_response() -> None:
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        await fake_mqtt.inject(
            f"cmd/{info.model_number}/{info.said}/response/{fake_mqtt.client_id}",
            {
                "requestId": "whatever",
                "timestamp": 1,
                "payload": state_mwo_full,
            },
        )

    task = asyncio.create_task(app.fetch_data())
    await fire_response()
    ok = await task
    assert ok is True
    assert app._state["primaryCavity"]["cavityState"] == "idle"

    # Verify getState was published on the request topic.
    request_topic = (
        f"cmd/{info.model_number}/{info.said}/request/{fake_mqtt.client_id}"
    )
    published_topics = [t for t, _ in fake_mqtt.published]
    assert request_topic in published_topics


async def test_fetch_data_times_out_returns_false(
    fake_mqtt, profile, info
) -> None:
    await fake_mqtt.connect()
    app = _ConcreteAppliance(fake_mqtt, info, profile, initial_state_timeout=0.05)
    await app.connect()
    fake_mqtt.clear_published()

    ok = await app.fetch_data()
    assert ok is False


async def test_state_delta_deep_merges(
    connected: _ConcreteAppliance, state_mwo_full, fake_mqtt, info
) -> None:
    import copy

    connected._state = copy.deepcopy(state_mwo_full)

    await fake_mqtt.inject(
        f"dt/{info.model_number}/{info.said}/state/update",
        {"primaryCavity": {"cavityLight": True}},
    )
    assert connected._state["primaryCavity"]["cavityLight"] is True
    # Sibling keys preserved.
    assert connected._state["primaryCavity"]["doorStatus"] == "closed"
    assert connected._state["hoodFan"]["userFanSpeed"] == "off"


async def test_presence_topics_update_online(
    connected: _ConcreteAppliance, fake_mqtt, info
) -> None:
    await fake_mqtt.inject(
        f"$aws/events/presence/connected/{info.said}", {}
    )
    assert connected.get_online() is True
    await fake_mqtt.inject(
        f"$aws/events/presence/disconnected/{info.said}", {}
    )
    assert connected.get_online() is False


async def test_callback_fanout_on_state_update(
    connected: _ConcreteAppliance, fake_mqtt, info
) -> None:
    calls: list[int] = []
    connected.register_attr_callback(lambda: calls.append(1))
    await fake_mqtt.inject(
        f"dt/{info.model_number}/{info.said}/state/update",
        {"primaryCavity": {"cavityLight": True}},
    )
    assert calls == [1]


async def test_callback_exception_does_not_break_fanout(
    connected: _ConcreteAppliance, fake_mqtt, info
) -> None:
    calls: list[str] = []

    def bad() -> None:
        calls.append("bad")
        raise RuntimeError("boom")

    def good() -> None:
        calls.append("good")

    connected.register_attr_callback(bad)
    connected.register_attr_callback(good)

    await fake_mqtt.inject(
        f"dt/{info.model_number}/{info.said}/state/update", {"a": 1}
    )
    assert calls == ["bad", "good"]


async def test_send_command_builds_payload(
    connected: _ConcreteAppliance, fake_mqtt, info
) -> None:
    fake_mqtt.clear_published()
    await connected._send_command("primaryCavity", "set", cavityLight=True)

    assert len(fake_mqtt.published) == 1
    topic, payload = fake_mqtt.published[0]
    assert topic == (
        f"cmd/{info.model_number}/{info.said}/request/{fake_mqtt.client_id}"
    )
    assert payload["payload"]["addressee"] == "primaryCavity"
    assert payload["payload"]["command"] == "set"
    assert payload["payload"]["cavityLight"] is True
    assert isinstance(payload["requestId"], str)
    assert len(payload["requestId"]) >= 8
    assert isinstance(payload["timestamp"], int)


async def test_reconnect_handler_refetches_state(
    fake_mqtt, profile, info, state_mwo_full
) -> None:
    await fake_mqtt.connect()
    app = _ConcreteAppliance(fake_mqtt, info, profile)
    await app.connect()
    fake_mqtt.clear_published()

    # Simulate a disconnect then reconnect — the appliance should re-publish getState.
    await fake_mqtt.simulate_disconnect()
    await fake_mqtt.simulate_reconnect()
    await asyncio.sleep(0)
    await asyncio.sleep(0)

    request_topic = (
        f"cmd/{info.model_number}/{info.said}/request/{fake_mqtt.client_id}"
    )
    assert any(t == request_topic for t, _ in fake_mqtt.published)
