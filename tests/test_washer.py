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

async def test_remote_control_enabled(appliances_manager: AppliancesManager):
    washer = appliances_manager.washers[0]
    assert washer.get_remote_control_enabled() is False


async def test_model_specific_capabilities_are_hidden_on_other_models(
    appliances_manager: AppliancesManager,
):
    washer = appliances_manager.washers[0]

    assert washer.is_cycle_options_model_supported() is False
    assert washer.get_wash_cycle_pair() is None
    assert washer.get_utility_cycle() is None
    assert washer.get_supported_specialty_cycles() == []
    assert washer.get_specialty_cycle() is None
    assert washer.supports_fan_fresh() is False
    assert washer.supports_steam() is False

