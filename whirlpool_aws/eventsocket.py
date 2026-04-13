import asyncio
import logging
import re
import uuid
from collections.abc import Callable
from socket import gaierror

import aiohttp

from .auth import Auth

LOGGER = logging.getLogger(__name__)

MSG_TERMINATION = "\n\n\0"

DATA_MSG_MATCHER = re.compile("{(.*)}\\x00")
TOKEN_INVALID_MSG_MATCHER = re.compile(".*Token Invalid.*")

WS_STATUS_GOING_AWAY = 1001
WS_STATUS_UNAUTHORIZED = 3000

RECONNECT_COUNT = 3
RECONNECT_SHORT_DELAY = 30
RECONNECT_LONG_DELAY = 60 * 4
GOING_AWAY_DELAY = (60 * 5) - RECONNECT_SHORT_DELAY


class EventSocket:
    """Event socket listener class"""

    def __init__(
        self,
        url: str,
        auth: Auth,
        said_list: list[str],
        msg_listener: Callable[[str], None],
        con_up_listener: Callable,
        session: aiohttp.ClientSession,
    ):
        self._url = url
        self._auth = auth
        self._said_list = said_list
        self._msg_listener = msg_listener
        self._running = False
        self._websocket: aiohttp.ClientWebSocketResponse | None = None
        self._run_future = None
        self._con_up_listener = con_up_listener
        self._reconnect_tries = RECONNECT_COUNT
        self._session = session

    def _create_connect_msg(self):
        return (
            "CONNECT\naccept-version:1.1,1.2\nheart-beat:30000,0\nwcloudtoken:"
            f"{self._auth.get_access_token()}"
        )

    async def _send_subscribe_messages(self, ws: aiohttp.ClientWebSocketResponse):
        # send one subscribe message for each said, with a unique id
        for said in self._said_list:
            id = uuid.uuid4()
            msg = f"SUBSCRIBE\nid:{id}\ndestination:/topic/{said}\nack:auto"
            await self._send_msg(ws, msg)

    async def _send_msg(self, websocket: aiohttp.ClientWebSocketResponse, msg):
        LOGGER.debug(f"> {msg}")
        await websocket.send_str(msg + MSG_TERMINATION)

    async def _recv_msg(self, websocket: aiohttp.ClientWebSocketResponse):
        msg = await websocket.receive()
        LOGGER.debug(f"< {msg}")
        return msg

    async def _run(self):
        while self._running:
            try:
                LOGGER.debug(f"Connecting to {self._url}")
                async with self._session.ws_connect(
                    self._url,
                    timeout=aiohttp.ClientWSTimeout(ws_receive=60, ws_close=60),  # type: ignore # ClientWSTimeout uses attr.s which pyright does not support
                    autoclose=True,
                    autoping=True,
                    heartbeat=45,
                ) as ws:
                    self._websocket = ws
                    self._reconnect_tries = RECONNECT_COUNT
                    connected_msg_done = False
                    subscribe_msg_done = False

                    while not ws.closed:
                        if not connected_msg_done:
                            await self._send_msg(ws, self._create_connect_msg())
                        elif not subscribe_msg_done:
                            await self._send_subscribe_messages(ws)

                        msg = await self._recv_msg(ws)
                        if not msg:
                            continue
                        if msg.type == aiohttp.WSMsgType.ERROR:
                            LOGGER.error("Socket message error")
                            break
                        if msg.type in [
                            aiohttp.WSMsgType.CLOSE,
                            aiohttp.WSMsgType.CLOSING,
                            aiohttp.WSMsgType.CLOSED,
                        ]:
                            LOGGER.info(
                                f"Stopping receiving. Message type: {str(msg.type)}"
                            )

                            if (
                                not self._auth.is_access_token_valid()
                                or msg.data == WS_STATUS_UNAUTHORIZED
                            ):
                                LOGGER.debug("auth key expired, doing reauth now")
                                while not await self._auth.do_auth():
                                    await asyncio.sleep(RECONNECT_LONG_DELAY)

                            elif msg.data == WS_STATUS_GOING_AWAY:
                                LOGGER.info(
                                    (
                                        "Received Going Away message: Waiting for %s"
                                        " seconds"
                                    ),
                                    GOING_AWAY_DELAY,
                                )
                                # Give server some time to come back up.
                                await asyncio.sleep(GOING_AWAY_DELAY)

                            break

                        invalid_token_match = TOKEN_INVALID_MSG_MATCHER.findall(
                            msg.data
                        )
                        if invalid_token_match:
                            LOGGER.debug("received invalid token msg, doing reauth now")
                            while not await self._auth.do_auth():
                                await asyncio.sleep(RECONNECT_LONG_DELAY)
                            break

                        if not connected_msg_done:
                            connected_msg_done = True
                            continue

                        if not subscribe_msg_done:
                            subscribe_msg_done = True
                            await self._con_up_listener()
                            continue

                        if msg.type != aiohttp.WSMsgType.TEXT:
                            LOGGER.error(
                                f"Socket message type is invalid: {str(msg.type)}"
                            )
                            continue

                        match = DATA_MSG_MATCHER.findall(msg.data)
                        if not match:
                            continue
                        self._msg_listener("{" + match[0] + "}")
            except (aiohttp.ClientError, TimeoutError, gaierror) as ex:
                LOGGER.error(f"Websocket could not connect: {ex}")

            self._websocket = None

            if self._running:
                self._reconnect_tries -= 1
                if self._reconnect_tries < 0:
                    self._reconnect_tries = 0
                    LOGGER.info(
                        f"Waiting to reconnect long delay {RECONNECT_LONG_DELAY}"
                        " seconds"
                    )

                    # Give server some time to come back up.
                    await asyncio.sleep(RECONNECT_LONG_DELAY)

                LOGGER.info(
                    f"Waiting to reconnect short delay {RECONNECT_SHORT_DELAY} seconds"
                )
                await asyncio.sleep(RECONNECT_SHORT_DELAY)

                LOGGER.info("Reconnecting...")

    def start(self):
        """Start the event socket listener"""
        self._running = True
        self._run_future = asyncio.get_event_loop().create_task(self._run())

    async def stop(self):
        """Stop the event socket listener"""
        self._running = False
        if not self._websocket:
            return
        await self._websocket.close()
        self._websocket = None
        if not self._run_future:
            return
        if not self._run_future.done():
            await self._run_future
