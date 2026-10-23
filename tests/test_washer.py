from typing import cast

from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.httpapi.washer import Washer
from whirlpool.washer import MachineState


async def test_attributes(appliances_manager: AppliancesManager):
    washer = cast(Washer, appliances_manager.washers[0])

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


async def test_model_specific_cycle_identity(
    appliances_manager: AppliancesManager,
):
    washer = cast(Washer, appliances_manager.washers[0])

    assert washer.get_wash_cycle_pair() is None
    assert washer.get_utility_cycle() is None

    washer.appliance_info.model_number = "WFW9620HBK3"
    assert washer.get_wash_cycle_pair() == ("whites", "cold_wash")
    assert washer.get_utility_cycle() is None

    washer.update_attributes({"WashCavity_CycleSetCycleSelect": 8}, 0)
    assert washer.get_wash_cycle_pair() is None
    assert washer.get_utility_cycle() == "drain_spin"
