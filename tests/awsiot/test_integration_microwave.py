import copy
from typing import Any
from unittest.mock import patch

from whirlpool.awsiot.appliancesmanager import AppliancesManager
from whirlpool.awsiot.capabilities import (
    CapabilityProfile,
    parse_capability_profile,
)
from whirlpool.microwave import HoodFanSpeed, MicrowaveCavityState
from whirlpool.microwave import Microwave as MicrowaveABC


class _FakeWhirlpoolAuth:
    async def get_access_token(self) -> str | None:
        return "token"


async def test_full_chain_start_and_state_update(
    fake_mqtt,
    client_session_fixture,
    capability_mwo_raw,
    thing_mwo,
    state_mwo_full,
):
    import whirlpool.awsiot.microwave  # noqa: F401

    async def fake_fetch(self) -> bool:
        self._state = copy.deepcopy(state_mwo_full)
        self._initial_state_event.set()
        return True

    async def fake_download(self, said, model, part) -> CapabilityProfile:
        return parse_capability_profile(capability_mwo_raw)

    class _FakeThings:
        def __init__(self, *args, **kwargs):
            pass

        async def list_things(self) -> list[dict[str, Any]]:
            return [thing_mwo]

    with (
        patch("whirlpool.awsiot.appliancesmanager.Things", _FakeThings),
        patch(
            "whirlpool.awsiot.appliancesmanager.MqttClient",
            return_value=fake_mqtt,
        ),
        patch(
            "whirlpool.awsiot.capabilities.CapabilityDownloader.get",
            fake_download,
        ),
        patch(
            "whirlpool.awsiot.appliance.Appliance.fetch_data",
            fake_fetch,
        ),
    ):
        manager = AppliancesManager(
            _FakeWhirlpoolAuth(), client_session_fixture, lambda: None  # type: ignore[arg-type]
        )
        ok = await manager.connect()
    assert ok is True

    assert len(manager.microwaves) == 1
    mwo = manager.microwaves[0]
    assert isinstance(mwo, MicrowaveABC)

    # Callback fanout.
    updates: list[int] = []
    mwo.register_attr_callback(lambda: updates.append(1))

    # State delta arrives: cooking transition.
    state_topic = (
        f"dt/{thing_mwo['thingTypeName']}/{thing_mwo['thingName']}/state/update"
    )
    await fake_mqtt.inject(
        state_topic,
        {"primaryCavity": {"cavityState": "cooking"}},
    )
    assert mwo.get_cavity_state() == MicrowaveCavityState.Cooking
    assert updates == [1]

    # Command path.
    fake_mqtt.clear_published()
    ok = await mwo.set_hood_fan_speed(HoodFanSpeed.High)
    assert ok is True
    topics = [t for t, _ in fake_mqtt.published]
    request_topic = (
        f"cmd/{thing_mwo['thingTypeName']}/{thing_mwo['thingName']}/request/"
        f"{fake_mqtt.client_id}"
    )
    assert request_topic in topics
