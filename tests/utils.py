import json
from pathlib import Path
from unittest.mock import Mock

from tests.aiohttp import AiohttpClientMocker
from tests.mock_backendselector import BackendSelectorMock

CURR_DIR = Path(__file__).parent
DATA_DIR = CURR_DIR / "data"
ACCOUNT_ID = "12345"


def get_mock_coro(return_value):
    async def mock_coro(*args, **kwargs):
        return return_value

    return Mock(wraps=mock_coro)


def assert_appliance_setter_call(
    appliance_http_client_mock: AiohttpClientMocker,
    said,
    expected_data_body,
    call_count,
):
    expected_cmd_data_base = {
        "header": {"said": said, "command": "setAttributes"},
    }
    mock_calls = appliance_http_client_mock.mock_calls
    assert len(mock_calls) == call_count
    assert mock_calls[-1][0] == "POST"
    assert mock_calls[-1][1].path == "/api/v1/appliance/command"
    assert mock_calls[-1][2] == expected_cmd_data_base | {"body": expected_data_body}


def mock_appliance_http_get(
    appliance_http_client_mock: AiohttpClientMocker,
    backend_selector_mock: BackendSelectorMock,
    said,
    data,
):
    appliance_http_client_mock.get(
        f"{backend_selector_mock.get_appliance_data_url}/{said}", json=data
    )


def mock_appliance_http_post(
    appliance_http_client_mock: AiohttpClientMocker,
    backend_selector_mock: BackendSelectorMock,
):
    appliance_http_client_mock.post(backend_selector_mock.post_appliance_command_url)


def mock_appliancesmanager_get_account_id_get(
    http_client_mock: AiohttpClientMocker,
    backend_selector_mock: BackendSelectorMock,
):
    http_client_mock.get(
        backend_selector_mock.get_user_data_url,
        content=json.dumps({"accountId": "12345"}).encode("utf-8"),
    )


def mock_appliancesmanager_get_owned_appliances_get(
    http_client_mock: AiohttpClientMocker,
    backend_selector_mock: BackendSelectorMock,
    account_id,
):
    with open(DATA_DIR / "owned_appliances.json") as f:
        owned_appliance_data = json.load(f)

    content = json.dumps({account_id: owned_appliance_data}).encode("utf-8")

    http_client_mock.get(
        f"{backend_selector_mock.get_owned_appliances_url}/{account_id}",
        content=content,
    )


def mock_appliancesmanager_get_shared_appliances_get(
    http_client_mock: AiohttpClientMocker,
    backend_selector_mock: BackendSelectorMock,
):
    with open(DATA_DIR / "shared_appliances.json") as f:
        shared_appliance_data = json.load(f)

    content = json.dumps(shared_appliance_data).encode("utf-8")

    http_client_mock.get(
        backend_selector_mock.get_shared_appliances_url, content=content
    )
