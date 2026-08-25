"""Tests for AWS IoT Appliance state handling."""

from unittest.mock import MagicMock

from whirlpool.awsiot.appliance import Appliance
from whirlpool.types import ApplianceInfo


def _make_appliance() -> Appliance:
    mqtt = MagicMock()
    mqtt.client_id = "client"
    info = ApplianceInfo(
        said="SAID", name="mw", category="cooking", model_number="M", serial_number="S"
    )
    return Appliance(mqtt, info)


class TestUpdateState:
    def test_partial_update_merges_into_existing_state(self) -> None:
        appliance = _make_appliance()
        appliance.update_state({"door": "closed", "hoodLight": "off", "fan": "off"})

        # dt/.../state/update messages only carry the changed attributes
        appliance.update_state({"hoodLight": "low"})

        assert appliance.get_raw_data() == {
            "door": "closed",
            "hoodLight": "low",
            "fan": "off",
        }

    def test_update_sets_initial_data_event_and_fires_callbacks(self) -> None:
        appliance = _make_appliance()
        callback = MagicMock()
        appliance.register_attr_callback(callback)

        appliance.update_state({"door": "open"})

        assert appliance._initial_data_event.is_set()
        callback.assert_called_once()
