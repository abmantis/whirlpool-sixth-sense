from whirlpool.appliancesmanager import AppliancesManager
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
    assert washer.get_door_open() is True
    assert washer.get_time_remaining() == 4080


async def test_supports_dispense_level(appliances_manager: AppliancesManager):
    # The HTTP washer reports its tank level, so it keeps the base default.
    assert appliances_manager.washers[0].supports_dispense_level() is True
