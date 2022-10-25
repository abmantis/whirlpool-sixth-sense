from tests.aiohttp import AiohttpClientMocker
from tests.mock_backendselector import BackendSelectorMock


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
        f"{backend_selector_mock.base_url}/api/v1/appliance/{said}",
        json=data,
    )


def mock_appliance_http_post(
    appliance_http_client_mock: AiohttpClientMocker,
    backend_selector_mock: BackendSelectorMock,
):
    appliance_http_client_mock.post(
        f"{backend_selector_mock.base_url}/api/v1/appliance/command"
    )
