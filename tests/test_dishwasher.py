import pytest

from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.washer import MachineState


@pytest.mark.parametrize(
    ("raw_state", "expected_state"),
    [("1", MachineState.Standby), ("3", MachineState.RunningMainCycle)],
)
async def test_attributes(
    appliances_manager: AppliancesManager,
    raw_state: str,
    expected_state: MachineState,
) -> None:
    """Test dishwasher attributes."""
    dishwasher = appliances_manager.dishwashers[0]
    dishwasher._set_attribute("Cavity_OperationStatusMachineState", raw_state, 0)

    assert dishwasher.get_machine_state() == expected_state
    assert dishwasher.get_door_open() is False
    assert dishwasher.get_time_remaining() == 4593
