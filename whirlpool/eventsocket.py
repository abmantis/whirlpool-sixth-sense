import aiohttp
import asyncio
import logging
import re
import uuid

from typing import Callable

from .auth import Auth

LOGGER = logging.getLogger(__name__)

WSURI = "wss://websocketservice.wcloud-emea.eu-gb.containers.appdomain.cloud/appliance/websocket"
MSG_TERMINATION = "\n\n\0"

RECV_MSG_MATCHER = re.compile("{(.*)}\\x00")


class EventSocket:
    def __init__(self, access_token, said, msg_listener: Callable[[str], None]):
        self._access_token = access_token
        self._said = said
        self._msg_listener = msg_listener
        self._running = False
        self._websocket: aiohttp.ClientWebSocketResponse = None
        self._run_future = None
        self._reconnect_tries = 3

    def _create_connect_msg(self):
        return f"CONNECT\nversion:1.1,1.0\nwcloudtoken:{self._access_token}"

    def _create_subscribe_msg(self):
        id = uuid.uuid4()
        return f"SUBSCRIBE\nid:{id}\ndestination:/topic/{self._said}\nack:auto"

    async def _send_msg(self, websocket: aiohttp.ClientWebSocketResponse, msg):
        LOGGER.debug(f"> {msg}")
        await websocket.send_str(msg + MSG_TERMINATION)

    async def _recv_msg(self, websocket: aiohttp.ClientWebSocketResponse):
        msg = await websocket.receive()
        LOGGER.debug(f"< {msg}")
        return msg

    async def _run(self):
        if not self._running:
            return

        timeout = aiohttp.ClientTimeout(total=None)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.ws_connect(
                WSURI, timeout=None, autoclose=True, autoping=True, heartbeat=45
            ) as ws:
                self._websocket = ws
                await self._send_msg(ws, self._create_connect_msg())
                await self._recv_msg(ws)
                await self._send_msg(ws, self._create_subscribe_msg())

                while not ws.closed:
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
                        LOGGER.debug(
                            f"Stopping receiving. Message type: {str(msg.type)}"
                        )
                        break
                    if msg.type != aiohttp.WSMsgType.TEXT:
                        LOGGER.error(f"Socket message type is invalid: {str(msg.type)}")
                        continue

                    match = RECV_MSG_MATCHER.findall(msg.data)
                    if not match:
                        continue
                    self._msg_listener("{" + match[0] + "}")

            self._websocket = None

        if self._running and self._reconnect_tries > 0:
            # TODO: add a timer to reset _reconnect_tries to 3 after 1 hour or so
            LOGGER.info("Reconnecting...")
            self._reconnect_tries = self._reconnect_tries - 1
            self._run_future = asyncio.get_event_loop().create_task(self._run())

    def start(self):
        self._running = True
        self._run_future = asyncio.get_event_loop().create_task(self._run())

    async def stop(self):
        self._running = False
        if not self._websocket:
            return
        await self._websocket.close()
        self._websocket = None

        await self._run_future
