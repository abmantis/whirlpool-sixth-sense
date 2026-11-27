import pytest

from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.httpapi.dishwasher import Dishwasher as HttpDishwasher
from whirlpool.washer import MachineState


def http_dishwasher(appliances_manager: AppliancesManager) -> HttpDishwasher:
    """Return the concrete HTTP API dishwasher for tests of private internals."""
    return appliances_manager._http_appliances_manager.dishwashers[0]


async def test_running_attributes_from_diagnostic_sample(
    appliances_manager: AppliancesManager,
) -> None:
    """Parse the running snapshot captured from JennAir JDTSS246GS0."""
    dishwasher = http_dishwasher(appliances_manager)

    assert dishwasher.get_machine_state() == MachineState.RunningMainCycle
    assert dishwasher.get_door_open() is False
    assert dishwasher.get_time_remaining() == 4593


async def test_idle_machine_state_from_diagnostic_sample(
    appliances_manager: AppliancesManager,
) -> None:
    """Map idle state 1 and open door observed in the JennAir report."""
    dishwasher = http_dishwasher(appliances_manager)
    dishwasher._set_attribute("Cavity_OperationStatusMachineState", "1", 1795221095917)
    dishwasher._set_attribute("Cavity_OperationStatusDoorOpen", "1", 1795221095917)

    assert dishwasher.get_machine_state() == MachineState.Standby
    assert dishwasher.get_door_open() is True


@pytest.mark.parametrize("raw_state", [None, "", "0", "2", "7", "99"])
async def test_unconfirmed_machine_states_are_unknown(
    appliances_manager: AppliancesManager,
    raw_state: str | None,
) -> None:
    """Missing or unobserved states stay unmapped (unobserved values are logged)."""
    dishwasher = http_dishwasher(appliances_manager)
    if raw_state is None:
        dishwasher._data_dict["attributes"].pop("Cavity_OperationStatusMachineState")
    else:
        dishwasher._set_attribute("Cavity_OperationStatusMachineState", raw_state, 0)

    assert dishwasher.get_machine_state() is None


async def test_unmapped_machine_state_is_logged(
    appliances_manager: AppliancesManager,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Unknown state codes are logged to make new samples discoverable."""
    dishwasher = http_dishwasher(appliances_manager)
    caplog.set_level("DEBUG", logger="whirlpool.httpapi.dishwasher")
    dishwasher._set_attribute("Cavity_OperationStatusMachineState", "99", 0)

    assert dishwasher.get_machine_state() is None
    assert f"Unmapped dishwasher machine state 99 for {dishwasher.said}" in caplog.text


async def test_dishwasher_model_is_not_classified_as_washer(
    appliances_manager: AppliancesManager,
) -> None:
    """Dishwashers (dishes) must not be exposed as clothes washers (laundry)."""
    dishwasher = appliances_manager.dishwashers[0]

    assert dishwasher.appliance_info.category == "Dishwasher"
    assert (
        dishwasher.appliance_info.raw_info["DATA_MODEL_KEY"]
        == "DDM_DISHWASHER_JA_DISH17_246_V1"
    )
    assert dishwasher not in appliances_manager.washers


async def test_dishwasher_category_classification_when_model_key_is_generic(
    appliances_manager: AppliancesManager,
) -> None:
    """The category identifies dishwasher payloads even with generic model keys."""
    manager = appliances_manager._http_appliances_manager
    appliance = dict(manager.all_appliances["SAIDDISHWASHER1"].appliance_info.raw_info)
    appliance["DATA_MODEL_KEY"] = "DDM_GENERIC_V1"

    manager._add_appliance(appliance)

    assert manager.dishwashers[-1].said == "SAIDDISHWASHER1"
    assert all(washer.said != "SAIDDISHWASHER1" for washer in manager.washers)


async def test_real_dishwasher_model_key_is_classified_as_dishwasher(
    appliances_manager: AppliancesManager,
) -> None:
    """The live JennAir model key is classified as a dishwasher, not washer."""
    manager = appliances_manager._http_appliances_manager
    appliance = dict(manager.all_appliances["SAIDDISHWASHER1"].appliance_info.raw_info)
    appliance["CATEGORY_NAME"] = "Other"

    manager._add_appliance(appliance)

    assert manager.dishwashers[-1].said == "SAIDDISHWASHER1"
    assert all(washer.said != "SAIDDISHWASHER1" for washer in manager.washers)
