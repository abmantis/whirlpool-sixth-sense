import asyncio
import logging
import re
import uuid
import websockets

from typing import Callable

from .auth import Auth

LOGGER = logging.getLogger(__name__)

WSURI = "wss://websocketservice.wcloud-emea.eu-gb.containers.appdomain.cloud/appliance/websocket"
MSG_TERMINATION = "\n\n\0"

RECV_MSG_MATCHER = re.compile('{(.*)}\x00')


class EventSocket():
    def __init__(self, access_token, said, msg_listener: Callable[[str],None]):
        self._access_token = access_token
        self._said = said
        self._msg_listener = msg_listener
        self._websocket: websockets.WebSocketClientProtocol = None
        self._run_future = None

    def _create_connect_msg(self):
        return f"CONNECT\nversion:1.1,1.0\nwcloudtoken:{self._access_token}"

    def _create_subscribe_msg(self):
        id = uuid.uuid4()
        return f"SUBSCRIBE\nid:{id}\ndestination:/topic/{self._said}\nack:auto"

    async def _send_msg(self, websocket, msg):
        LOGGER.debug(f"> {msg}")
        await websocket.send(msg + MSG_TERMINATION)

    async def _recv_msg(self, websocket: websockets.WebSocketClientProtocol):
        try:
            msg = await websocket.recv()
            LOGGER.debug(f"< {msg}")
            return msg
        except websockets.exceptions.ConnectionClosedOK:
            pass

        return None

    async def _run(self):
        async with websockets.connect(WSURI) as websocket:
            self._websocket = websocket
            await self._send_msg(websocket, self._create_connect_msg())
            await self._recv_msg(websocket)
            await self._send_msg(websocket, self._create_subscribe_msg())

            while(self._websocket):
                msg = await self._recv_msg(websocket)
                if not msg:
                    continue

                match = RECV_MSG_MATCHER.findall(msg)
                if not match:
                    continue
                self._msg_listener("{" + match[0] + "}")

    def start(self):
        self._run_future = asyncio.get_event_loop().create_task(self._run())

    async def stop(self):
        if not self._websocket:
            return
        await self._websocket.close()
        self._websocket = None

        await self._run_future
