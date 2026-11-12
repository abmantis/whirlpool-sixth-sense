from unittest.mock import Mock

import pytest

from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.awsiot.mqttclient import MqttClient
from whirlpool.awsiot.washer import Washer as AwsWasher
from whirlpool.httpapi.washer import Washer
from whirlpool.types import ApplianceInfo
from whirlpool.washer import MachineState


async def test_attributes(appliances_manager: AppliancesManager):
    washer = appliances_manager.washers[0]

    assert washer.get_machine_state() == MachineState.Standby
    assert washer.get_cycle_status_sensing() is False
    assert washer.get_cycle_status_filling() is False
    assert washer.get_cycle_status_soaking() is False
    assert washer.get_cycle_status_washing() is False
    assert washer.get_cycle_status_rinsing() is False
    assert washer.get_cycle_status_spinning() is False
    assert washer.get_dispense_1_level() == 4
    assert washer.get_dispense_2_level() is None
    assert washer.get_door_open() is True
    assert washer.get_time_remaining() == 4080


async def test_remote_control_enabled(appliances_manager: AppliancesManager):
    washer = appliances_manager.washers[0]
    assert washer.get_remote_control_enabled() is False

    raw_data = washer.get_raw_data()
    assert raw_data is not None
    raw_data["attributes"].pop("XCat_RemoteSetRemoteControlEnable")
    assert washer.get_remote_control_enabled() is None


async def test_secondary_dispenser_level(appliances_manager: AppliancesManager):
    washer = appliances_manager.washers[0]
    assert isinstance(washer, Washer)
    assert washer.get_dispense_2_level() is None
    assert washer.get_dispense_1_level() == 4

    raw_data = washer.get_raw_data()
    assert raw_data is not None
    raw_data["attributes"]["WashCavity_OpStatusBulkDispense2Level"] = {
        "value": "0",
        "updateTime": 0,
    }
    washer.update_attributes({"WashCavity_OpStatusBulkDispense2Level": 7}, 1)

    assert washer.get_dispense_2_level() == 7
    assert washer.get_dispense_1_level() == 4


def test_awsiot_washer_unsupported_getters():
    washer = AwsWasher(
        Mock(spec=MqttClient),
        ApplianceInfo("said", "name", "washer", "model", "serial"),
    )

    with pytest.raises(NotImplementedError):
        washer.get_remote_control_enabled()
    with pytest.raises(NotImplementedError):
        washer.get_dispense_2_level()
