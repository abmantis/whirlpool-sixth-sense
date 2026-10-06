import pytest
from aiointercept import aiointercept
from yarl import URL

from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.auth import Auth
from whirlpool.backendselector import BackendSelector
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


@pytest.mark.parametrize(
    ("method_name", "operation"),
    (("start", "2"), ("pause", "5"), ("resume", "6"), ("cancel", "1")),
)
async def test_command_setters(
    appliances_manager: AppliancesManager,
    auth: Auth,
    backend_selector: BackendSelector,
    aiointercept_mock: aiointercept,
    method_name: str,
    operation: str,
):
    washer = appliances_manager.washers[0]
    url = backend_selector.appliance_command_url
    expected_json = {
        "body": {"Cavity_OpSetOperations": operation},
        "header": {"said": washer.said, "command": "setAttributes"},
    }
    aiointercept_mock.post(url, payload=expected_json)

    assert await getattr(washer, method_name)()

    aiointercept_mock.assert_called_with(
        url=url,
        method="POST",
        data=None,
        json=expected_json,
        headers=auth.create_headers(),
    )
    assert len(aiointercept_mock.requests[("POST", URL(url))]) == 1


async def test_remote_control_enabled(appliances_manager: AppliancesManager):
    washer = appliances_manager.washers[0]
    assert washer.get_remote_control_enabled() is False
