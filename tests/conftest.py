import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from .aiohttp import AiohttpClientMocker
from .mock_backendselector import BackendSelectorMock


@pytest.fixture
def http_client_mock(mocker, backend_selector_mock):
    """Set up aiohttp ClientSession mock."""
    http_client_mocker = AiohttpClientMocker()
    mocker.patch(
        "aiohttp.ClientSession",
        side_effect=lambda *args, **kwargs: http_client_mocker.create_session(
            asyncio.get_event_loop()
        ),
    )
    return http_client_mocker


@pytest.fixture
def appliance_http_client_mock(http_client_mock, backend_selector_mock):
    http_client_mock.get(
        f"{backend_selector_mock.base_url}/api/v1/client_auth/webSocketUrl",
        json={"url": "wss://something"},
    )

    # async def ws_get_side_effect(method, url, data, headers):
    #     ws_key: str = headers[hdrs.SEC_WEBSOCKET_KEY]
    #     accept_key = base64.b64encode(
    #         hashlib.sha1(ws_key.encode("utf-8") + http_websocket.WS_KEY).digest()
    #     ).decode()
    #     return AiohttpClientMockResponse(
    #         method=method,
    #         url=url,
    #         status=HTTPStatus.SWITCHING_PROTOCOLS,
    #         headers={
    #             hdrs.UPGRADE: "websocket",
    #             hdrs.CONNECTION: "upgrade",
    #             hdrs.SEC_WEBSOCKET_ACCEPT: accept_key,
    #         },
    #     )
    # appliance_httpclient.get(
    #     "wss://something",
    #     json={},
    #     status=HTTPStatus.SWITCHING_PROTOCOLS,
    #     headers={
    #         hdrs.UPGRADE: "websocket",
    #         hdrs.CONNECTION: "upgrade",
    #         hdrs.SEC_WEBSOCKET_ACCEPT: "s3pPLMBiTxaQ9kYGzzhZRbK",
    #     },
    #     side_effect=ws_get_side_effect,
    # )

    return http_client_mock


@pytest.fixture
def backend_selector_mock():
    return BackendSelectorMock()


@pytest.fixture
def auth_mock():
    return MagicMock()


@pytest.fixture(autouse=True)
def event_socket_mock(mocker):
    event_socket = mocker.patch("whirlpool.appliance.EventSocket").return_value
    event_socket.stop = AsyncMock()
    return event_socket
