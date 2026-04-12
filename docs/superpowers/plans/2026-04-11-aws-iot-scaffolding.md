# AWS IoT Scaffolding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fill in `whirlpool/awsiot/` with an async-safe MQTT client, capability-file-driven appliance factory, a top-level `Microwave` ABC, and a concrete KitchenAid MWO implementation — proving the architecture end-to-end.

**Architecture:** Keep the two-transport facade in `whirlpool/appliancesmanager.py`. Rewrite `MqttClient` to be async-safe (paho on its own thread, dispatch loop on the event loop). Add `capabilities.py` for capability file download + parse, `factory.py` for class routing by `CapabilityProfile`, `matchers.py` for declarative class registration. Slim `awsiot.Appliance` into a thin base with `_get_path*` helpers + `_send_command`. Add `whirlpool/microwave.py` ABC. Implement `awsiot/microwave.py` as the first concrete AWS-side subclass; register stub AWS subclasses for the other categories so contributors have a template.

**Tech Stack:** Python 3.11+, asyncio, aiohttp, paho-mqtt (kept, not replaced), pytest + pytest-asyncio (auto mode), basedpyright, ruff.

**Spec:** `docs/superpowers/specs/2026-04-11-aws-iot-scaffolding-design.md`

---

## Working assumptions

- The working tree is `/home/paulsites/projects/whirlpool-sixth-sense`, currently on branch `aws_iot-scaffolding` (forked off `origin/aws_iot`).
- The design spec at `docs/superpowers/specs/2026-04-11-aws-iot-scaffolding-design.md` is already committed.
- `pytest`, `ruff`, `basedpyright` are installed via `pip install -r requirements-dev.txt`. Run `pip install -r requirements-dev.txt` once before starting if the venv is fresh.
- The exact schema of the capability file is not known yet; all capability-related fixtures in this plan are **plausible placeholders** synthesized from the MQTT payloads observed in `/home/paulsites/projects/kitchenaid_dev/tools/kitchenaid_iot.py`. They will be replaced with real captures in Task 21.
- Wire-level state shapes for the microwave (`primaryCavity`, `hoodFan`, top-level `hoodLight` string, etc.) **are** known from `kitchenaid_iot.py` and are used as-is in the state fixtures.

## Conventions for every task

- Every test file starts with `from __future__ import annotations` omitted (this codebase uses Python 3.11+ `str | None` syntax natively — match abmantis's style).
- Do NOT add `@pytest.mark.asyncio` — `pytest.ini` has `asyncio_mode = auto`.
- Run `ruff check whirlpool tests` and `basedpyright` after every task and fix any issues before committing.
- Never `git add -A` or `git add .` — name files explicitly.
- Commit messages follow conventional-commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`), optionally scoped with `(awsiot)`.

## File structure (what this plan will create or modify)

**New production files:**
- `whirlpool/microwave.py` — top-level `Microwave` ABC + enums
- `whirlpool/httpapi/microwave.py` — `NotImplementedError` stub (ABC inheritance only)
- `whirlpool/awsiot/capabilities.py` — `CapabilityProfile`, `CapabilityDownloader`, `CapabilityDownloadError`
- `whirlpool/awsiot/factory.py` — `ApplianceFactory`, `DEFAULT_FACTORY`, `register_appliance` decorator
- `whirlpool/awsiot/matchers.py` — matcher helpers (`has_addressee`, `has_feature`, `all_of`, etc.)
- `whirlpool/awsiot/microwave.py` — concrete AWS-side `Microwave`
- `whirlpool/awsiot/oven.py` — category stub (factory-registered, raises `NotImplementedError`)
- `whirlpool/awsiot/aircon.py` — category stub
- `whirlpool/awsiot/dryer.py` — category stub
- `whirlpool/awsiot/washer.py` — category stub
- `whirlpool/awsiot/refrigerator.py` — category stub

**Modified production files:**
- `whirlpool/awsiot/mqttclient.py` — async-safe rewrite; keeps `MQTT_ENDPOINT`, SigV4 URL flow, TLS setup
- `whirlpool/awsiot/appliance.py` — slimmed base class: `_state` dict, deep merge, `_get_path*` helpers, `_send_command`, presence tracking, lifecycle
- `whirlpool/awsiot/appliancesmanager.py` — uses factory + capability downloader; isinstance-based category routing against ABCs
- `whirlpool/appliancesmanager.py` — facade `microwaves` property; routes `_update_appliances`
- `whirlpool/httpapi/appliancesmanager.py` — add `_microwaves: dict` and `microwaves` property for symmetry

**New test files:**
- `tests/awsiot/__init__.py`
- `tests/awsiot/conftest.py` — `FakeMqttClient`, fixtures
- `tests/awsiot/data/capability_mwo.json`
- `tests/awsiot/data/capability_mwo_no_hood.json`
- `tests/awsiot/data/thing_mwo.json`
- `tests/awsiot/data/state_mwo_full.json`
- `tests/awsiot/data/state_mwo_cooking.json`
- `tests/awsiot/test_capabilities.py`
- `tests/awsiot/test_factory.py`
- `tests/awsiot/test_matchers.py`
- `tests/awsiot/test_mqttclient.py`
- `tests/awsiot/test_appliance_base.py`
- `tests/awsiot/test_microwave.py`
- `tests/awsiot/test_appliancesmanager.py`
- `tests/awsiot/test_integration_microwave.py`

**New tooling:**
- `tools/__init__.py` (if missing)
- `tools/capture_mwo_fixtures.py` — capture helper used against the real device

---

## Task 1: Scaffold the `tests/awsiot/` directory

**Files:**
- Create: `tests/awsiot/__init__.py`
- Create: `tests/awsiot/data/.gitkeep`

- [ ] **Step 1: Create `tests/awsiot/__init__.py`** with this exact content:

```python
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
```

- [ ] **Step 2: Create `tests/awsiot/data/.gitkeep`** as an empty file (ensures git tracks the directory before JSON fixtures are added).

- [ ] **Step 3: Verify layout**

Run: `ls tests/awsiot tests/awsiot/data`
Expected: shows `__init__.py` in `tests/awsiot`, `.gitkeep` in `tests/awsiot/data`.

- [ ] **Step 4: Commit**

```bash
git add tests/awsiot/__init__.py tests/awsiot/data/.gitkeep
git commit -m "test(awsiot): scaffold awsiot test directory"
```

---

## Task 2: Hand-crafted JSON fixtures

These fixtures are synthesized from the payload shapes observed in `tools/kitchenaid_iot.py`. Tests written against them remain valid when real captures replace them in Task 21, because the tests read paths that both shapes satisfy. `capability_mwo.json` is provisional — the `CapabilityProfile` parser in Task 5 normalizes it into a stable shape that downstream tests rely on.

**Files:**
- Create: `tests/awsiot/data/capability_mwo.json`
- Create: `tests/awsiot/data/capability_mwo_no_hood.json`
- Create: `tests/awsiot/data/thing_mwo.json`
- Create: `tests/awsiot/data/state_mwo_full.json`
- Create: `tests/awsiot/data/state_mwo_cooking.json`

- [ ] **Step 1: Create `tests/awsiot/data/capability_mwo.json`**

```json
{
  "capabilityPartNumber": "W11650000",
  "modelFamily": "KitchenAid MWO",
  "features": [
    "microwaveOven",
    "hoodFan",
    "hoodLight",
    "hoodLightColor",
    "cavityLight",
    "remoteStart",
    "controlLockout",
    "quietMode",
    "sabbathMode"
  ],
  "addressees": {
    "appliance": {
      "commands": ["getState"]
    },
    "primaryCavity": {
      "commands": ["run", "set", "cancel", "pause", "resume"]
    },
    "hoodFan": {
      "commands": ["set"]
    },
    "hoodLight": {
      "commands": ["set"]
    },
    "hoodLightColor": {
      "commands": ["set"]
    }
  },
  "metadata": {
    "applianceType": "microwave",
    "overTheRange": true
  }
}
```

- [ ] **Step 2: Create `tests/awsiot/data/capability_mwo_no_hood.json`** (hood-less counter-top variant for feature-gating tests)

```json
{
  "capabilityPartNumber": "W11650001",
  "modelFamily": "KitchenAid MWO CT",
  "features": [
    "microwaveOven",
    "cavityLight",
    "remoteStart",
    "controlLockout",
    "quietMode",
    "sabbathMode"
  ],
  "addressees": {
    "appliance": {
      "commands": ["getState"]
    },
    "primaryCavity": {
      "commands": ["run", "set", "cancel", "pause", "resume"]
    }
  },
  "metadata": {
    "applianceType": "microwave",
    "overTheRange": false
  }
}
```

- [ ] **Step 3: Create `tests/awsiot/data/thing_mwo.json`** (shape mirrors what `Things.list_things()` returns from AWS IoT `DescribeThing`)

```json
{
  "thingName": "WPR1A00000001",
  "thingTypeName": "KMMC5019JBS",
  "attributes": {
    "Name": "4b69746368656e204d6963726f77617665",
    "Category": "Cooking",
    "Brand": "KITCHENAID",
    "Serial": "D12345678",
    "CapabilityPartNumber": "W11650000",
    "supportsRemoteRecipes": "true"
  }
}
```

- [ ] **Step 4: Create `tests/awsiot/data/state_mwo_full.json`** (snapshot of idle MWO with hood + door closed)

```json
{
  "primaryCavity": {
    "cavityState": "idle",
    "doorStatus": "closed",
    "doorLockStatus": "unlocked",
    "recipeId": "",
    "recipeExecutionState": "IDLE",
    "mwoPowerLevel": 0,
    "cavityLight": false,
    "turnTable": "enabled",
    "ovenDisplayTemperature": 0,
    "cookTimer": {
      "state": "idle",
      "time": 0,
      "timeComplete": 0
    }
  },
  "hoodFan": {
    "userFanSpeed": "off"
  },
  "hoodLight": "off",
  "hoodLightColor": "warmWhite",
  "temperatureUnit": "fahrenheit",
  "remoteStartEnable": true,
  "hmiControlLockout": false,
  "quietMode": false,
  "sabbathMode": false
}
```

- [ ] **Step 5: Create `tests/awsiot/data/state_mwo_cooking.json`** (active 30s cook at 80% power)

```json
{
  "primaryCavity": {
    "cavityState": "cooking",
    "doorStatus": "closed",
    "doorLockStatus": "unlocked",
    "recipeId": "microwave",
    "recipeExecutionState": "RUNNING",
    "mwoPowerLevel": 80,
    "cavityLight": true,
    "turnTable": "enabled",
    "ovenDisplayTemperature": 0,
    "cookTimer": {
      "state": "running",
      "time": 30,
      "timeComplete": 1712345708
    }
  },
  "hoodFan": {
    "userFanSpeed": "off"
  },
  "hoodLight": "off",
  "hoodLightColor": "warmWhite",
  "temperatureUnit": "fahrenheit",
  "remoteStartEnable": true,
  "hmiControlLockout": false,
  "quietMode": false,
  "sabbathMode": false
}
```

- [ ] **Step 6: Remove the placeholder `.gitkeep`**

```bash
rm tests/awsiot/data/.gitkeep
```

- [ ] **Step 7: Commit**

```bash
git add tests/awsiot/data/capability_mwo.json tests/awsiot/data/capability_mwo_no_hood.json tests/awsiot/data/thing_mwo.json tests/awsiot/data/state_mwo_full.json tests/awsiot/data/state_mwo_cooking.json
git rm tests/awsiot/data/.gitkeep
git commit -m "test(awsiot): add placeholder MWO fixture data"
```

---

## Task 3: `FakeMqttClient` and shared fixtures in `tests/awsiot/conftest.py`

The fake is the main test vehicle for every awsiot test except `test_mqttclient.py` (which mocks paho directly). It must match the public interface that `MqttClient` will expose after the Task 4 refactor. Building the fake first fixes the interface before the real client is touched.

**Files:**
- Create: `tests/awsiot/conftest.py`

- [ ] **Step 1: Create `tests/awsiot/conftest.py`**

```python
import json
from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from whirlpool.types import ApplianceInfo

from . import DATA_DIR

MessageHandler = Callable[[str, dict[str, Any]], Awaitable[None]]
ConnectionHandler = Callable[[], Awaitable[None]]


class FakeMqttClient:
    """In-memory stand-in for whirlpool.awsiot.MqttClient.

    Implements the same public surface the real client exposes so tests
    can drive messages, assert published traffic, and simulate connection
    lifecycle events without touching paho or the network.
    """

    def __init__(self, client_id: str = "fake-identity_deadbeefcafef00d") -> None:
        self._connected: bool = False
        self._client_id: str = client_id
        self.subscriptions: set[str] = set()
        self.published: list[tuple[str, dict[str, Any]]] = []
        self._message_handlers: list[MessageHandler] = []
        self._on_connect_handlers: list[ConnectionHandler] = []
        self._on_disconnect_handlers: list[ConnectionHandler] = []

    # --- lifecycle -------------------------------------------------------

    async def connect(self) -> bool:
        self._connected = True
        for handler in list(self._on_connect_handlers):
            await handler()
        return True

    async def disconnect(self) -> None:
        self._connected = False
        for handler in list(self._on_disconnect_handlers):
            await handler()

    def is_connected(self) -> bool:
        return self._connected

    @property
    def client_id(self) -> str | None:
        return self._client_id if self._connected else None

    # --- pub/sub ---------------------------------------------------------

    async def subscribe(self, topic: str) -> None:
        self.subscriptions.add(topic)

    async def unsubscribe(self, topic: str) -> None:
        self.subscriptions.discard(topic)

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        self.published.append((topic, payload))

    # --- handler registration -------------------------------------------

    def add_message_handler(self, handler: MessageHandler) -> None:
        self._message_handlers.append(handler)

    def remove_message_handler(self, handler: MessageHandler) -> None:
        try:
            self._message_handlers.remove(handler)
        except ValueError:
            pass

    def add_connection_handler(
        self,
        on_connect: ConnectionHandler | None = None,
        on_disconnect: ConnectionHandler | None = None,
    ) -> None:
        if on_connect is not None:
            self._on_connect_handlers.append(on_connect)
        if on_disconnect is not None:
            self._on_disconnect_handlers.append(on_disconnect)

    # --- test-only driving API ------------------------------------------

    async def inject(self, topic: str, payload: dict[str, Any]) -> None:
        """Fire registered handlers as if a message arrived on `topic`."""
        for handler in list(self._message_handlers):
            await handler(topic, payload)

    async def simulate_disconnect(self) -> None:
        self._connected = False
        for handler in list(self._on_disconnect_handlers):
            await handler()

    async def simulate_reconnect(self) -> None:
        self._connected = True
        for handler in list(self._on_connect_handlers):
            await handler()

    def clear_published(self) -> None:
        self.published.clear()


def _load_json(name: str) -> dict[str, Any]:
    with open(DATA_DIR / name) as f:
        return json.load(f)


@pytest.fixture
def fake_mqtt() -> FakeMqttClient:
    return FakeMqttClient()


@pytest.fixture
def capability_mwo_raw() -> dict[str, Any]:
    return _load_json("capability_mwo.json")


@pytest.fixture
def capability_mwo_no_hood_raw() -> dict[str, Any]:
    return _load_json("capability_mwo_no_hood.json")


@pytest.fixture
def thing_mwo() -> dict[str, Any]:
    return _load_json("thing_mwo.json")


@pytest.fixture
def state_mwo_full() -> dict[str, Any]:
    return _load_json("state_mwo_full.json")


@pytest.fixture
def state_mwo_cooking() -> dict[str, Any]:
    return _load_json("state_mwo_cooking.json")


@pytest.fixture
def appliance_info_mwo(thing_mwo: dict[str, Any]) -> ApplianceInfo:
    return ApplianceInfo(
        said=thing_mwo["thingName"],
        name=bytes.fromhex(thing_mwo["attributes"]["Name"]).decode("utf-8"),
        category=thing_mwo["attributes"]["Category"].lower(),
        model_number=thing_mwo["thingTypeName"],
        serial_number=thing_mwo["attributes"]["Serial"],
    )
```

- [ ] **Step 2: Smoke-test the conftest** by writing a throwaway test assertion so pytest can import and collect it.

Run: `pytest tests/awsiot --collect-only -q`
Expected: no collection errors (no tests yet — just imports and fixtures).

- [ ] **Step 3: Commit**

```bash
git add tests/awsiot/conftest.py
git commit -m "test(awsiot): add FakeMqttClient and shared fixtures"
```

---

## Task 4: Refactor `MqttClient` to be async-safe

The existing client has a module-level TODO warning its `publish`/`subscribe`/`unsubscribe` are not async-safe, and `_on_message` runs arbitrary callbacks on the paho network thread. This task rewrites those boundaries and replaces the single-callback API with a handler list. No test file yet — Task 5 tests it.

**Files:**
- Modify: `whirlpool/awsiot/mqttclient.py` (full rewrite, keeps `MQTT_ENDPOINT`, `_generate_client_id`, SigV4 URL + TLS setup)

- [ ] **Step 1: Replace `whirlpool/awsiot/mqttclient.py` with the async-safe implementation**

```python
"""Whirlpool AWS IoT MQTT Client (async-safe)."""

import asyncio
import json
import logging
import secrets
import ssl
import urllib.parse
from collections.abc import Awaitable, Callable
from typing import Any

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion, MQTTProtocolVersion
from paho.mqtt.properties import Properties
from paho.mqtt.reasoncodes import ReasonCode

from .auth import Auth

LOGGER = logging.getLogger(__name__)

MQTT_ENDPOINT = "wt.applianceconnect.net"
CONNECT_TIMEOUT_SECONDS = 10.0
RECONNECT_BACKOFF_CAP_SECONDS = 30.0

MessageHandler = Callable[[str, dict[str, Any]], Awaitable[None]]
ConnectionHandler = Callable[[], Awaitable[None]]


def _generate_client_id(identity_id: str) -> str:
    """Generate a client ID in the format used by the Android app."""
    random_suffix = secrets.token_hex(8)  # 16 hex chars
    return f"{identity_id}_{random_suffix}"


class MqttClient:
    """Async-safe MQTT client for Whirlpool AWS IoT.

    All public methods are coroutines or sync accessors. Paho runs in its
    own network thread; incoming messages are marshalled onto the asyncio
    loop through a queue, and handlers never run on the paho thread.
    """

    def __init__(self, aws_auth: Auth) -> None:
        self._aws_auth = aws_auth
        self._client: mqtt.Client | None = None
        self._connected = asyncio.Event()
        self._subscribed_topics: set[str] = set()
        self._client_id: str | None = None

        self._loop = asyncio.get_running_loop()
        self._incoming: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()
        self._dispatch_task: asyncio.Task[None] | None = None

        self._message_handlers: list[MessageHandler] = []
        self._on_connect_handlers: list[ConnectionHandler] = []
        self._on_disconnect_handlers: list[ConnectionHandler] = []

    # --- lifecycle -------------------------------------------------------

    async def connect(self) -> bool:
        signed_url = await self._aws_auth.create_signed_url(MQTT_ENDPOINT)
        client_id = await self._generate_client_id_async()

        LOGGER.debug("MQTT Client ID: %s", client_id)
        LOGGER.debug("Connecting to wss://%s/mqtt", MQTT_ENDPOINT)

        client = mqtt.Client(
            client_id=client_id,
            transport="websockets",
            protocol=MQTTProtocolVersion.MQTTv311,
            callback_api_version=CallbackAPIVersion.VERSION2,
        )
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        client.on_disconnect = self._on_disconnect
        client.on_subscribe = self._on_subscribe

        parsed_url = urllib.parse.urlparse(signed_url)
        path_with_query = f"{parsed_url.path}?{parsed_url.query}"
        client.ws_set_options(
            path=path_with_query,
            headers={
                "Host": MQTT_ENDPOINT,
                "Sec-WebSocket-Protocol": "mqtt",
            },
        )
        client.username_pw_set(username="?SDK=Android&Version=2.75.0", password=None)
        client.tls_set(
            ca_certs=None,
            certfile=None,
            keyfile=None,
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLS_CLIENT,
        )

        try:
            await self._loop.run_in_executor(
                None, lambda: client.connect(MQTT_ENDPOINT, port=443, keepalive=30)
            )
        except Exception as e:
            LOGGER.error("Failed to connect to MQTT broker: %s", e)
            return False

        client.loop_start()
        self._client = client

        try:
            await asyncio.wait_for(
                self._connected.wait(), timeout=CONNECT_TIMEOUT_SECONDS
            )
        except TimeoutError:
            LOGGER.error("MQTT connection timeout")
            client.loop_stop()
            self._client = None
            return False

        self._client_id = client_id
        self._dispatch_task = self._loop.create_task(self._dispatch_loop())
        return True

    async def disconnect(self) -> None:
        if self._dispatch_task is not None:
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass
            self._dispatch_task = None

        if self._client is not None:
            client = self._client
            await self._loop.run_in_executor(None, client.loop_stop)
            await self._loop.run_in_executor(None, client.disconnect)
            self._client = None

        self._connected.clear()
        self._client_id = None

    def is_connected(self) -> bool:
        return self._connected.is_set()

    @property
    def client_id(self) -> str | None:
        return self._client_id

    # --- pub/sub ---------------------------------------------------------

    async def subscribe(self, topic: str) -> None:
        self._subscribed_topics.add(topic)
        if self._client is not None and self._connected.is_set():
            client = self._client
            await self._loop.run_in_executor(
                None, lambda: client.subscribe(topic, qos=1)
            )

    async def unsubscribe(self, topic: str) -> None:
        self._subscribed_topics.discard(topic)
        if self._client is not None and self._connected.is_set():
            client = self._client
            await self._loop.run_in_executor(None, lambda: client.unsubscribe(topic))

    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        if self._client is None or not self._connected.is_set():
            LOGGER.warning("Cannot publish, MQTT client not connected")
            return
        client = self._client
        body = json.dumps(payload)
        await self._loop.run_in_executor(
            None, lambda: client.publish(topic, body, qos=1)
        )

    # --- handler registration -------------------------------------------

    def add_message_handler(self, handler: MessageHandler) -> None:
        self._message_handlers.append(handler)

    def remove_message_handler(self, handler: MessageHandler) -> None:
        try:
            self._message_handlers.remove(handler)
        except ValueError:
            pass

    def add_connection_handler(
        self,
        on_connect: ConnectionHandler | None = None,
        on_disconnect: ConnectionHandler | None = None,
    ) -> None:
        if on_connect is not None:
            self._on_connect_handlers.append(on_connect)
        if on_disconnect is not None:
            self._on_disconnect_handlers.append(on_disconnect)

    # --- internals -------------------------------------------------------

    async def _generate_client_id_async(self) -> str:
        identity_id = await self._aws_auth.get_cognito_identity_id()
        if not identity_id:
            raise RuntimeError("Failed to get Cognito identity ID")
        return _generate_client_id(identity_id)

    async def _dispatch_loop(self) -> None:
        while True:
            topic, payload = await self._incoming.get()
            for handler in list(self._message_handlers):
                try:
                    await handler(topic, payload)
                except Exception:
                    LOGGER.exception(
                        "Message handler raised for topic %s", topic
                    )

    def _on_connect(
        self,
        client: mqtt.Client,
        _userdata: Any,
        _connect_flags: mqtt.ConnectFlags,
        reason_code: ReasonCode,
        _properties: Properties | None = None,
    ) -> None:
        if reason_code.is_failure:
            LOGGER.error("MQTT connection failed: %s", reason_code)
            return

        LOGGER.debug(
            "MQTT connected, resubscribing %d topics", len(self._subscribed_topics)
        )
        for topic in self._subscribed_topics:
            client.subscribe(topic, qos=1)

        self._loop.call_soon_threadsafe(self._connected.set)
        self._loop.call_soon_threadsafe(self._fire_on_connect_handlers)

    def _fire_on_connect_handlers(self) -> None:
        for handler in list(self._on_connect_handlers):
            self._loop.create_task(self._run_connection_handler(handler))

    def _fire_on_disconnect_handlers(self) -> None:
        for handler in list(self._on_disconnect_handlers):
            self._loop.create_task(self._run_connection_handler(handler))

    async def _run_connection_handler(self, handler: ConnectionHandler) -> None:
        try:
            await handler()
        except Exception:
            LOGGER.exception("Connection handler raised")

    def _on_message(
        self, _client: mqtt.Client, _userdata: Any, msg: mqtt.MQTTMessage
    ) -> None:
        # Runs on paho's network thread. Must NOT touch asyncio state
        # directly — marshal onto the event loop.
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            LOGGER.warning("Failed to decode MQTT message on %s: %s", msg.topic, e)
            return

        topic = msg.topic
        self._loop.call_soon_threadsafe(self._incoming.put_nowait, (topic, payload))

    def _on_disconnect(
        self,
        _client: mqtt.Client,
        _userdata: Any,
        _disconnect_flags: mqtt.DisconnectFlags,
        reason_code: ReasonCode,
        _properties: Properties | None = None,
    ) -> None:
        if reason_code.is_failure:
            LOGGER.warning("MQTT unexpected disconnect: %s", reason_code)
        else:
            LOGGER.debug("MQTT disconnected cleanly")

        self._loop.call_soon_threadsafe(self._connected.clear)
        self._loop.call_soon_threadsafe(self._fire_on_disconnect_handlers)

    def _on_subscribe(
        self,
        _client: mqtt.Client,
        _userdata: Any,
        mid: int,
        granted_qos: list[ReasonCode],
        _properties: Properties | None = None,
    ) -> None:
        LOGGER.debug(
            "MQTT subscription confirmed (mid=%d, qos=%s)", mid, granted_qos
        )
```

- [ ] **Step 2: Update the existing `AppliancesManager` import site so it still compiles.**

Open `whirlpool/awsiot/appliancesmanager.py:45`. The current line is:

```python
self._mqtt = MqttClient(self._aws_auth, self._handle_mqtt_message)
```

Change it to:

```python
self._mqtt = MqttClient(self._aws_auth)
```

(The old `message_callback` parameter is gone; Task 16 rewires dispatch through appliance-level handlers. This temporary state is OK — tests in Task 5 drive `MqttClient` directly, and Task 16 replaces the rest.)

- [ ] **Step 3: Type-check and lint**

Run: `ruff check whirlpool/awsiot/mqttclient.py whirlpool/awsiot/appliancesmanager.py`
Expected: PASS.

Run: `basedpyright whirlpool/awsiot/mqttclient.py`
Expected: PASS (module compiles in isolation; downstream type errors in `appliancesmanager.py` are allowed at this point — they are fixed in Task 16).

- [ ] **Step 4: Commit**

```bash
git add whirlpool/awsiot/mqttclient.py whirlpool/awsiot/appliancesmanager.py
git commit -m "refactor(awsiot): make MqttClient async-safe"
```

---

## Task 5: `test_mqttclient.py` — paho-mocked unit tests

This is the only test file that exercises real `MqttClient` code. Paho's `Client` class is patched with a `MagicMock` so tests drive its callbacks directly.

**Files:**
- Create: `tests/awsiot/test_mqttclient.py`

- [ ] **Step 1: Write the failing test file**

```python
import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from whirlpool.awsiot.mqttclient import MqttClient


@pytest.fixture
def mock_aws_auth() -> AsyncMock:
    auth = AsyncMock()
    auth.create_signed_url.return_value = (
        "wss://wt.applianceconnect.net/mqtt?X-Amz-Algorithm=fake"
    )
    auth.get_cognito_identity_id.return_value = "fake-identity-id"
    return auth


async def _flush() -> None:
    # Let scheduled tasks and soon-callbacks drain.
    await asyncio.sleep(0)
    await asyncio.sleep(0)


@pytest.fixture
def fake_paho() -> MagicMock:
    """A MagicMock standing in for paho.mqtt.client.Client.

    Stores the last-instantiated instance so tests can trigger callbacks.
    """
    instance = MagicMock(name="paho.Client")
    instance.connect.return_value = None
    instance.publish.return_value = None
    instance.subscribe.return_value = None
    instance.unsubscribe.return_value = None
    return instance


async def _build_client(mock_aws_auth: AsyncMock, fake_paho: MagicMock) -> MqttClient:
    with patch(
        "whirlpool.awsiot.mqttclient.mqtt.Client", return_value=fake_paho
    ):
        client = MqttClient(mock_aws_auth)

        async def do_connect() -> bool:
            return await client.connect()

        task = asyncio.create_task(do_connect())
        # Let connect() schedule the paho connect + start the loop.
        await _flush()
        # Simulate paho firing on_connect callback.
        fake_paho.on_connect(
            fake_paho, None, MagicMock(), MagicMock(is_failure=False), None
        )
        await _flush()
        connected = await task
        assert connected is True
    return client


class TestConnectAndPublish:
    async def test_connect_awaits_connected_event_and_starts_loop(
        self, mock_aws_auth: AsyncMock, fake_paho: MagicMock
    ) -> None:
        client = await _build_client(mock_aws_auth, fake_paho)
        assert client.is_connected()
        assert client.client_id is not None
        fake_paho.loop_start.assert_called_once()
        await client.disconnect()

    async def test_publish_serializes_payload_and_calls_paho(
        self, mock_aws_auth: AsyncMock, fake_paho: MagicMock
    ) -> None:
        client = await _build_client(mock_aws_auth, fake_paho)
        await client.publish("topic/x", {"hello": "world"})
        fake_paho.publish.assert_called_once()
        args, kwargs = fake_paho.publish.call_args
        assert args[0] == "topic/x"
        assert '"hello"' in args[1]
        assert kwargs.get("qos") == 1
        await client.disconnect()

    async def test_subscribe_records_topic_and_calls_paho(
        self, mock_aws_auth: AsyncMock, fake_paho: MagicMock
    ) -> None:
        client = await _build_client(mock_aws_auth, fake_paho)
        await client.subscribe("topic/y")
        fake_paho.subscribe.assert_called_with("topic/y", qos=1)
        await client.disconnect()


class TestDispatchLoop:
    async def test_message_handlers_run_on_event_loop_not_paho_thread(
        self, mock_aws_auth: AsyncMock, fake_paho: MagicMock
    ) -> None:
        client = await _build_client(mock_aws_auth, fake_paho)

        received: list[tuple[str, dict[str, Any]]] = []
        running_loop_capture: list[asyncio.AbstractEventLoop] = []

        async def handler(topic: str, payload: dict[str, Any]) -> None:
            running_loop_capture.append(asyncio.get_running_loop())
            received.append((topic, payload))

        client.add_message_handler(handler)

        msg = MagicMock()
        msg.topic = "dt/model/said/state/update"
        msg.payload = b'{"primaryCavity": {"cavityLight": true}}'
        # _on_message is called by paho on its own thread in prod;
        # here we just invoke it directly to verify the marshalling path.
        client._on_message(fake_paho, None, msg)
        await _flush()

        assert received == [
            ("dt/model/said/state/update", {"primaryCavity": {"cavityLight": True}})
        ]
        assert running_loop_capture[0] is asyncio.get_running_loop()
        await client.disconnect()

    async def test_handler_exception_does_not_break_dispatch_loop(
        self, mock_aws_auth: AsyncMock, fake_paho: MagicMock
    ) -> None:
        client = await _build_client(mock_aws_auth, fake_paho)

        calls: list[str] = []

        async def bad(topic: str, payload: dict[str, Any]) -> None:
            calls.append("bad")
            raise RuntimeError("boom")

        async def good(topic: str, payload: dict[str, Any]) -> None:
            calls.append("good")

        client.add_message_handler(bad)
        client.add_message_handler(good)

        msg1 = MagicMock()
        msg1.topic = "t"
        msg1.payload = b"{}"
        client._on_message(fake_paho, None, msg1)
        await _flush()

        msg2 = MagicMock()
        msg2.topic = "t"
        msg2.payload = b"{}"
        client._on_message(fake_paho, None, msg2)
        await _flush()

        assert calls == ["bad", "good", "bad", "good"]
        await client.disconnect()

    async def test_malformed_payload_is_dropped(
        self, mock_aws_auth: AsyncMock, fake_paho: MagicMock
    ) -> None:
        client = await _build_client(mock_aws_auth, fake_paho)

        received: list[Any] = []

        async def handler(topic: str, payload: dict[str, Any]) -> None:
            received.append((topic, payload))

        client.add_message_handler(handler)

        msg = MagicMock()
        msg.topic = "t"
        msg.payload = b"not json {"
        client._on_message(fake_paho, None, msg)
        await _flush()

        assert received == []
        await client.disconnect()


class TestConnectionHandlers:
    async def test_on_connect_handler_fires_after_connect(
        self, mock_aws_auth: AsyncMock, fake_paho: MagicMock
    ) -> None:
        client = await _build_client(mock_aws_auth, fake_paho)
        fired: list[bool] = []

        async def handler() -> None:
            fired.append(True)

        client.add_connection_handler(on_connect=handler)

        # Simulate paho firing on_connect again (e.g., after reconnect).
        fake_paho.on_connect(
            fake_paho, None, MagicMock(), MagicMock(is_failure=False), None
        )
        await _flush()
        assert fired == [True]
        await client.disconnect()
```

- [ ] **Step 2: Run the tests — expect them to pass**

Run: `pytest tests/awsiot/test_mqttclient.py -v`
Expected: all tests PASS.

- [ ] **Step 3: If any test fails**, fix the minimal surface in `whirlpool/awsiot/mqttclient.py`, rerun until green. Do NOT modify the tests.

- [ ] **Step 4: Commit**

```bash
git add tests/awsiot/test_mqttclient.py
git commit -m "test(awsiot): unit-test async MqttClient against mocked paho"
```

---

## Task 6: `whirlpool/awsiot/capabilities.py` — `CapabilityProfile` dataclass

Starts with the dataclass and parser. The downloader comes in Task 7.

**Files:**
- Create: `whirlpool/awsiot/capabilities.py`
- Create: `tests/awsiot/test_capabilities.py`

- [ ] **Step 1: Write the failing test file for the profile + parser**

```python
import pytest

from whirlpool.awsiot.capabilities import (
    CapabilityDownloadError,
    CapabilityProfile,
    parse_capability_profile,
)


class TestParseCapabilityProfile:
    def test_parses_features_addressees_commands(
        self, capability_mwo_raw: dict
    ) -> None:
        profile = parse_capability_profile(capability_mwo_raw)
        assert isinstance(profile, CapabilityProfile)
        assert profile.part_number == "W11650000"
        assert "microwaveOven" in profile.features
        assert "hoodFan" in profile.addressees
        assert "primaryCavity" in profile.addressees
        assert profile.supports_command("primaryCavity", "run") is True
        assert profile.supports_command("primaryCavity", "nonesuch") is False
        assert profile.has_feature("microwaveOven") is True
        assert profile.has_addressee("hoodFan") is True

    def test_raw_preserved(self, capability_mwo_raw: dict) -> None:
        profile = parse_capability_profile(capability_mwo_raw)
        assert profile.raw == capability_mwo_raw
        assert profile.metadata.get("applianceType") == "microwave"

    def test_missing_part_number_raises(self) -> None:
        with pytest.raises(CapabilityDownloadError):
            parse_capability_profile({"features": []})

    def test_missing_addressees_defaults_to_empty(self) -> None:
        profile = parse_capability_profile(
            {"capabilityPartNumber": "X", "features": ["a"]}
        )
        assert profile.addressees == frozenset()
        assert profile.commands == {}

    def test_no_hood_profile(self, capability_mwo_no_hood_raw: dict) -> None:
        profile = parse_capability_profile(capability_mwo_no_hood_raw)
        assert profile.has_addressee("hoodFan") is False
        assert profile.has_feature("microwaveOven") is True
```

- [ ] **Step 2: Run the test — expect FAIL (module does not exist)**

Run: `pytest tests/awsiot/test_capabilities.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'whirlpool.awsiot.capabilities'`.

- [ ] **Step 3: Create `whirlpool/awsiot/capabilities.py` with the dataclass + parser**

```python
"""Capability file download, parsing, and caching.

Issue #122: the Whirlpool cloud exposes capability files via an MQTT
request/response topic pair, not via HTTPS. This module owns that flow
and produces a normalized CapabilityProfile that the factory consumes
to route appliances to the right subclass.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import Awaitable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import aiohttp

from .mqttclient import MqttClient

LOGGER = logging.getLogger(__name__)

CAPABILITY_DOWNLOAD_TIMEOUT = 10.0


class CapabilityDownloadError(Exception):
    """Raised when a capability file cannot be retrieved or parsed."""


@dataclass(frozen=True)
class CapabilityProfile:
    """Parsed capability file for a single appliance model."""

    part_number: str
    raw: dict[str, Any]
    features: frozenset[str]
    addressees: frozenset[str]
    commands: dict[str, frozenset[str]] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def has_feature(self, feature: str) -> bool:
        return feature in self.features

    def has_addressee(self, addressee: str) -> bool:
        return addressee in self.addressees

    def supports_command(self, addressee: str, command: str) -> bool:
        return command in self.commands.get(addressee, frozenset())


def parse_capability_profile(raw: dict[str, Any]) -> CapabilityProfile:
    """Normalize a raw capability file dict into a CapabilityProfile.

    Shape assumptions (provisional until real files are captured):
      - `capabilityPartNumber`: str (required)
      - `features`: list[str]
      - `addressees`: dict[name -> {"commands": list[str]}]
      - `metadata`: optional dict
    """
    part_number = raw.get("capabilityPartNumber")
    if not isinstance(part_number, str) or not part_number:
        raise CapabilityDownloadError(
            "Capability file is missing 'capabilityPartNumber'"
        )

    features_list = raw.get("features") or []
    if not isinstance(features_list, list):
        raise CapabilityDownloadError("Capability 'features' is not a list")
    features = frozenset(str(f) for f in features_list)

    addressees_obj = raw.get("addressees") or {}
    if not isinstance(addressees_obj, dict):
        raise CapabilityDownloadError("Capability 'addressees' is not a dict")

    commands: dict[str, frozenset[str]] = {}
    for name, spec in addressees_obj.items():
        cmds: list[str] = []
        if isinstance(spec, dict):
            cmd_list = spec.get("commands") or []
            if isinstance(cmd_list, list):
                cmds = [str(c) for c in cmd_list]
        commands[str(name)] = frozenset(cmds)

    metadata = raw.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}

    return CapabilityProfile(
        part_number=part_number,
        raw=raw,
        features=features,
        addressees=frozenset(commands.keys()),
        commands=commands,
        metadata=metadata,
    )
```

- [ ] **Step 4: Run the tests — expect PASS**

Run: `pytest tests/awsiot/test_capabilities.py -v`
Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add whirlpool/awsiot/capabilities.py tests/awsiot/test_capabilities.py
git commit -m "feat(awsiot): add CapabilityProfile dataclass and parser"
```

---

## Task 7: `CapabilityDownloader` — MQTT-driven download with in-memory + disk cache

**Files:**
- Modify: `whirlpool/awsiot/capabilities.py` (add the downloader class)
- Modify: `tests/awsiot/test_capabilities.py` (add downloader tests)

- [ ] **Step 1: Add downloader tests to `tests/awsiot/test_capabilities.py`**

Append to the existing test file:

```python
from pathlib import Path
from typing import Any

import pytest
from aioresponses import aioresponses

from whirlpool.awsiot.capabilities import CapabilityDownloader


class _FakeSession:
    """Minimal aiohttp.ClientSession stand-in for tests."""

    def __init__(self, url_to_body: dict[str, dict[str, Any]]) -> None:
        self._url_to_body = url_to_body

    def get(self, url: str):  # noqa: D401
        body = self._url_to_body[url]

        class _Ctx:
            async def __aenter__(self_inner):
                class _Resp:
                    status = 200

                    async def json(self_r):
                        return body

                    async def text(self_r):
                        return json.dumps(body)

                return _Resp()

            async def __aexit__(self_inner, *args):
                return None

        import json
        return _Ctx()


async def test_downloader_publishes_request_and_returns_profile(
    fake_mqtt, capability_mwo_raw
) -> None:
    download_url = "https://capfiles.example.com/W11650000.json"
    session = _FakeSession({download_url: capability_mwo_raw})
    downloader = CapabilityDownloader(fake_mqtt, session)  # type: ignore[arg-type]

    said = "WPR1A00000001"
    model = "KMMC5019JBS"
    part = "W11650000"

    async def fire_response() -> None:
        # Give downloader time to subscribe + publish.
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        await fake_mqtt.inject(
            f"api/capability/download/{model}/{said}/response",
            {"url": download_url, "capabilityPartNumber": part},
        )

    import asyncio
    task = asyncio.create_task(downloader.get(said, model, part))
    await fire_response()
    profile = await task

    assert profile.part_number == part
    assert profile.has_feature("microwaveOven")

    # Verify the request topic + payload.
    request_topic = f"api/capability/download/{model}/{said}"
    assert any(
        topic == request_topic and payload.get("capabilityPartNumber") == part
        for topic, payload in fake_mqtt.published
    )


async def test_downloader_in_memory_cache_hit_skips_mqtt(
    fake_mqtt, capability_mwo_raw
) -> None:
    download_url = "https://capfiles.example.com/W11650000.json"
    session = _FakeSession({download_url: capability_mwo_raw})
    downloader = CapabilityDownloader(fake_mqtt, session)  # type: ignore[arg-type]

    import asyncio

    async def fire_response() -> None:
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        await fake_mqtt.inject(
            "api/capability/download/KMMC5019JBS/WPR1A00000001/response",
            {"url": download_url, "capabilityPartNumber": "W11650000"},
        )

    task = asyncio.create_task(
        downloader.get("WPR1A00000001", "KMMC5019JBS", "W11650000")
    )
    await fire_response()
    await task

    fake_mqtt.clear_published()

    # Second call should hit in-memory cache and NOT publish.
    profile = await downloader.get("WPR1A00000001", "KMMC5019JBS", "W11650000")
    assert profile.part_number == "W11650000"
    assert fake_mqtt.published == []


async def test_downloader_timeout_raises(fake_mqtt) -> None:
    session = _FakeSession({})
    downloader = CapabilityDownloader(
        fake_mqtt, session, timeout=0.05  # type: ignore[arg-type]
    )
    from whirlpool.awsiot.capabilities import CapabilityDownloadError

    with pytest.raises(CapabilityDownloadError):
        await downloader.get("SAID", "MODEL", "PART")


async def test_downloader_disk_cache_hit(
    fake_mqtt, capability_mwo_raw, tmp_path: Path
) -> None:
    # Pre-seed disk cache.
    import json

    cache_dir = tmp_path / "caps"
    cache_dir.mkdir()
    (cache_dir / "W11650000.json").write_text(json.dumps(capability_mwo_raw))

    session = _FakeSession({})
    downloader = CapabilityDownloader(
        fake_mqtt, session, cache_dir=cache_dir  # type: ignore[arg-type]
    )

    profile = await downloader.get("SAID", "MODEL", "W11650000")
    assert profile.part_number == "W11650000"
    assert fake_mqtt.published == []
```

- [ ] **Step 2: Run the tests — expect FAIL (`CapabilityDownloader` does not exist)**

Run: `pytest tests/awsiot/test_capabilities.py -v`
Expected: ImportError / AttributeError.

- [ ] **Step 3: Add `CapabilityDownloader` to `whirlpool/awsiot/capabilities.py`**

Append to the bottom of the existing file:

```python
class CapabilityDownloader:
    """Downloads capability files over MQTT, parses them, caches the result."""

    def __init__(
        self,
        mqtt: MqttClient,
        session: aiohttp.ClientSession,
        cache_dir: Path | None = None,
        timeout: float = CAPABILITY_DOWNLOAD_TIMEOUT,
    ) -> None:
        self._mqtt = mqtt
        self._session = session
        self._cache_dir = cache_dir
        self._timeout = timeout
        self._memory_cache: dict[str, CapabilityProfile] = {}

    async def get(
        self,
        said: str,
        model_number: str,
        capability_part_number: str,
    ) -> CapabilityProfile:
        cached = self._memory_cache.get(capability_part_number)
        if cached is not None:
            LOGGER.debug("Capability cache hit (memory) for %s", capability_part_number)
            return cached

        disk_hit = self._load_from_disk(capability_part_number)
        if disk_hit is not None:
            LOGGER.debug("Capability cache hit (disk) for %s", capability_part_number)
            profile = parse_capability_profile(disk_hit)
            self._memory_cache[capability_part_number] = profile
            return profile

        LOGGER.debug(
            "Downloading capability file %s for said=%s", capability_part_number, said
        )
        raw = await self._download(said, model_number, capability_part_number)
        profile = parse_capability_profile(raw)
        self._memory_cache[capability_part_number] = profile
        self._save_to_disk(capability_part_number, raw)
        return profile

    async def _download(
        self, said: str, model_number: str, capability_part_number: str
    ) -> dict[str, Any]:
        response_topic = f"api/capability/download/{model_number}/{said}/response"
        request_topic = f"api/capability/download/{model_number}/{said}"

        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()

        async def handler(topic: str, payload: dict[str, Any]) -> None:
            if topic != response_topic:
                return
            if not future.done():
                future.set_result(payload)

        self._mqtt.add_message_handler(handler)
        try:
            await self._mqtt.subscribe(response_topic)
            await self._mqtt.publish(
                request_topic,
                {
                    "requestId": str(uuid.uuid4()),
                    "capabilityPartNumber": capability_part_number,
                },
            )
            try:
                response = await asyncio.wait_for(future, timeout=self._timeout)
            except TimeoutError as e:
                raise CapabilityDownloadError(
                    f"Timed out waiting for capability file for {said}"
                ) from e

            download_url = response.get("url") or response.get("downloadUrl")
            if isinstance(download_url, str) and download_url.startswith("http"):
                return await self._fetch_capability_url(download_url)
            # Fall-through: the response itself may BE the capability.
            return response
        finally:
            self._mqtt.remove_message_handler(handler)
            await self._mqtt.unsubscribe(response_topic)

    async def _fetch_capability_url(self, url: str) -> dict[str, Any]:
        async with self._session.get(url) as resp:
            if resp.status != 200:
                raise CapabilityDownloadError(
                    f"Capability URL returned HTTP {resp.status}"
                )
            text = await resp.text()
            try:
                return json.loads(text)
            except json.JSONDecodeError as e:
                raise CapabilityDownloadError(
                    f"Capability body is not valid JSON: {e}"
                ) from e

    def _load_from_disk(self, part_number: str) -> dict[str, Any] | None:
        if self._cache_dir is None:
            return None
        path = self._cache_dir / f"{part_number}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as e:
            LOGGER.warning("Ignoring unreadable capability cache %s: %s", path, e)
            return None

    def _save_to_disk(self, part_number: str, raw: dict[str, Any]) -> None:
        if self._cache_dir is None:
            return
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            (self._cache_dir / f"{part_number}.json").write_text(json.dumps(raw))
        except OSError as e:
            LOGGER.warning("Failed to write capability cache for %s: %s", part_number, e)
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `pytest tests/awsiot/test_capabilities.py -v`
Expected: all capability tests PASS.

- [ ] **Step 5: Lint + typecheck**

Run: `ruff check whirlpool/awsiot/capabilities.py tests/awsiot/test_capabilities.py`
Expected: PASS.

Run: `basedpyright whirlpool/awsiot/capabilities.py`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add whirlpool/awsiot/capabilities.py tests/awsiot/test_capabilities.py
git commit -m "feat(awsiot): add CapabilityDownloader with memory + disk cache (#122)"
```

---

## Task 8: `matchers.py` and `test_matchers.py`

Tiny DSL that the factory consumes; depends only on `CapabilityProfile` from Task 6.

**Files:**
- Create: `whirlpool/awsiot/matchers.py`
- Create: `tests/awsiot/test_matchers.py`

- [ ] **Step 1: Write the failing test file**

```python
from typing import Any

import pytest

from whirlpool.awsiot.capabilities import parse_capability_profile
from whirlpool.awsiot.matchers import (
    all_of,
    any_of,
    has_addressee,
    has_command,
    has_feature,
    model_prefix,
    not_,
    thing_category,
)


@pytest.fixture
def profile(capability_mwo_raw: dict[str, Any]):
    return parse_capability_profile(capability_mwo_raw)


@pytest.fixture
def profile_no_hood(capability_mwo_no_hood_raw: dict[str, Any]):
    return parse_capability_profile(capability_mwo_no_hood_raw)


def test_has_feature(profile, thing_mwo):
    assert has_feature("microwaveOven")(profile, thing_mwo) is True
    assert has_feature("deepFryer")(profile, thing_mwo) is False


def test_has_addressee(profile, profile_no_hood, thing_mwo):
    assert has_addressee("hoodFan")(profile, thing_mwo) is True
    assert has_addressee("hoodFan")(profile_no_hood, thing_mwo) is False


def test_has_command(profile, thing_mwo):
    assert has_command("primaryCavity", "run")(profile, thing_mwo) is True
    assert has_command("primaryCavity", "detonate")(profile, thing_mwo) is False


def test_model_prefix(profile, thing_mwo):
    assert model_prefix("KMMC")(profile, thing_mwo) is True
    assert model_prefix("ABCD")(profile, thing_mwo) is False


def test_thing_category(profile, thing_mwo):
    assert thing_category("cooking")(profile, thing_mwo) is True
    assert thing_category("laundry")(profile, thing_mwo) is False


def test_all_of_any_of_not(profile, profile_no_hood, thing_mwo):
    combined = all_of(has_feature("microwaveOven"), has_addressee("primaryCavity"))
    assert combined(profile, thing_mwo) is True

    either = any_of(has_addressee("hoodFan"), has_feature("nope"))
    assert either(profile, thing_mwo) is True
    assert either(profile_no_hood, thing_mwo) is False

    negated = not_(has_addressee("hoodFan"))
    assert negated(profile, thing_mwo) is False
    assert negated(profile_no_hood, thing_mwo) is True
```

- [ ] **Step 2: Run — expect FAIL (module missing)**

Run: `pytest tests/awsiot/test_matchers.py -v`
Expected: ImportError.

- [ ] **Step 3: Create `whirlpool/awsiot/matchers.py`**

```python
"""Matcher helpers used by the ApplianceFactory for class routing.

Each helper returns a callable with the signature
`(CapabilityProfile, thing_dict) -> bool`. Subclasses combine matchers
through `all_of`, `any_of`, `not_` to declare when they should fire.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .capabilities import CapabilityProfile

Matcher = Callable[[CapabilityProfile, dict[str, Any]], bool]


def has_feature(name: str) -> Matcher:
    def _match(profile: CapabilityProfile, _thing: dict[str, Any]) -> bool:
        return profile.has_feature(name)

    return _match


def has_addressee(name: str) -> Matcher:
    def _match(profile: CapabilityProfile, _thing: dict[str, Any]) -> bool:
        return profile.has_addressee(name)

    return _match


def has_command(addressee: str, command: str) -> Matcher:
    def _match(profile: CapabilityProfile, _thing: dict[str, Any]) -> bool:
        return profile.supports_command(addressee, command)

    return _match


def model_prefix(prefix: str) -> Matcher:
    def _match(_profile: CapabilityProfile, thing: dict[str, Any]) -> bool:
        model = thing.get("thingTypeName", "")
        return isinstance(model, str) and model.startswith(prefix)

    return _match


def thing_category(name: str) -> Matcher:
    target = name.lower()

    def _match(_profile: CapabilityProfile, thing: dict[str, Any]) -> bool:
        attrs = thing.get("attributes") or {}
        category = str(attrs.get("Category", "")).lower()
        return category == target

    return _match


def all_of(*matchers: Matcher) -> Matcher:
    def _match(profile: CapabilityProfile, thing: dict[str, Any]) -> bool:
        return all(m(profile, thing) for m in matchers)

    return _match


def any_of(*matchers: Matcher) -> Matcher:
    def _match(profile: CapabilityProfile, thing: dict[str, Any]) -> bool:
        return any(m(profile, thing) for m in matchers)

    return _match


def not_(matcher: Matcher) -> Matcher:
    def _match(profile: CapabilityProfile, thing: dict[str, Any]) -> bool:
        return not matcher(profile, thing)

    return _match
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `pytest tests/awsiot/test_matchers.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add whirlpool/awsiot/matchers.py tests/awsiot/test_matchers.py
git commit -m "feat(awsiot): add matcher helpers for class routing"
```

---

## Task 9: `factory.py` and `test_factory.py`

**Files:**
- Create: `whirlpool/awsiot/factory.py`
- Create: `tests/awsiot/test_factory.py`

- [ ] **Step 1: Write the failing test file**

```python
import logging
from typing import Any

import pytest

from whirlpool.awsiot.capabilities import parse_capability_profile
from whirlpool.awsiot.factory import ApplianceFactory, register_appliance
from whirlpool.awsiot.matchers import has_addressee, has_feature
from whirlpool.types import ApplianceInfo


class _StubBase:
    def __init__(
        self,
        mqtt: Any,
        appliance_info: ApplianceInfo,
        capability_profile: Any,
    ) -> None:
        self.mqtt = mqtt
        self.info = appliance_info
        self.profile = capability_profile


@pytest.fixture
def info() -> ApplianceInfo:
    return ApplianceInfo(
        said="S", name="n", category="cooking",
        model_number="M", serial_number="X",
    )


@pytest.fixture
def mwo_profile(capability_mwo_raw):
    return parse_capability_profile(capability_mwo_raw)


def test_registration_and_priority(mwo_profile, thing_mwo, info):
    factory = ApplianceFactory()

    class HighMatch(_StubBase):
        pass

    class LowMatch(_StubBase):
        pass

    factory.register(
        LowMatch, matcher=has_addressee("primaryCavity"), priority=1
    )
    factory.register(
        HighMatch,
        matcher=lambda p, t: has_addressee("primaryCavity")(p, t)
        and has_feature("microwaveOven")(p, t),
        priority=10,
    )

    built = factory.build(object(), mwo_profile, thing_mwo, info)
    assert isinstance(built, HighMatch)


def test_build_returns_none_when_no_matcher_fires(mwo_profile, thing_mwo, info):
    factory = ApplianceFactory()

    class Nada(_StubBase):
        pass

    factory.register(Nada, matcher=has_feature("nonexistent"), priority=5)
    assert factory.build(object(), mwo_profile, thing_mwo, info) is None


def test_tie_break_first_registered_wins(
    mwo_profile, thing_mwo, info, caplog: pytest.LogCaptureFixture
):
    factory = ApplianceFactory()

    class First(_StubBase):
        pass

    class Second(_StubBase):
        pass

    factory.register(First, matcher=has_addressee("primaryCavity"), priority=5)
    factory.register(Second, matcher=has_addressee("primaryCavity"), priority=5)

    with caplog.at_level(logging.WARNING, logger="whirlpool.awsiot.factory"):
        built = factory.build(object(), mwo_profile, thing_mwo, info)
    assert isinstance(built, First)
    assert any("tie" in r.message.lower() for r in caplog.records)


def test_decorator_registers_in_default_factory(mwo_profile, thing_mwo, info):
    from whirlpool.awsiot.factory import DEFAULT_FACTORY

    marker: list[type] = []

    @register_appliance(
        matcher=has_feature("microwaveOven"), priority=100, factory=DEFAULT_FACTORY,
    )
    class Decorated(_StubBase):
        pass

    marker.append(Decorated)
    built = DEFAULT_FACTORY.build(object(), mwo_profile, thing_mwo, info)
    # Decorated should win vs anything else already registered at a lower priority.
    assert isinstance(built, marker[0])
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest tests/awsiot/test_factory.py -v`
Expected: ImportError.

- [ ] **Step 3: Create `whirlpool/awsiot/factory.py`**

```python
"""Appliance class factory driven by CapabilityProfile matchers."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .matchers import Matcher

if TYPE_CHECKING:
    from .appliance import Appliance
    from .capabilities import CapabilityProfile
    from .mqttclient import MqttClient
    from ..types import ApplianceInfo

LOGGER = logging.getLogger(__name__)


@dataclass
class Registration:
    cls: type
    matcher: Matcher
    priority: int
    order: int  # insertion order, used for deterministic tie-break


class ApplianceFactory:
    def __init__(self) -> None:
        self._registrations: list[Registration] = []
        self._counter: int = 0

    def register(
        self,
        cls: type,
        matcher: Matcher,
        priority: int = 0,
    ) -> None:
        self._registrations.append(
            Registration(cls=cls, matcher=matcher, priority=priority, order=self._counter)
        )
        self._counter += 1

    def build(
        self,
        mqtt: "MqttClient",
        profile: "CapabilityProfile",
        thing: dict[str, Any],
        appliance_info: "ApplianceInfo",
    ) -> "Appliance | None":
        matching: list[Registration] = [
            r for r in self._registrations if r.matcher(profile, thing)
        ]
        if not matching:
            return None

        matching.sort(key=lambda r: (-r.priority, r.order))
        top = matching[0]

        if len(matching) > 1 and matching[1].priority == top.priority:
            LOGGER.warning(
                "Capability %s matched multiple classes at priority %d; tie broken"
                " by registration order. First-registered=%s; others=%s",
                profile.part_number,
                top.priority,
                top.cls.__name__,
                [r.cls.__name__ for r in matching[1:] if r.priority == top.priority],
            )

        return top.cls(mqtt, appliance_info, profile)


DEFAULT_FACTORY = ApplianceFactory()


def register_appliance(
    matcher: Matcher,
    priority: int = 0,
    factory: ApplianceFactory | None = None,
) -> Callable[[type], type]:
    """Decorator for subclasses to self-register at import time."""

    target_factory = factory if factory is not None else DEFAULT_FACTORY

    def decorate(cls: type) -> type:
        target_factory.register(cls, matcher=matcher, priority=priority)
        return cls

    return decorate
```

- [ ] **Step 4: Run the tests — expect PASS**

Run: `pytest tests/awsiot/test_factory.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add whirlpool/awsiot/factory.py tests/awsiot/test_factory.py
git commit -m "feat(awsiot): add ApplianceFactory with priority + decorator"
```

---

## Task 10: `whirlpool/microwave.py` top-level ABC + enums

No transport dependency. Lives at the top level alongside `oven.py`.

**Files:**
- Create: `whirlpool/microwave.py`

- [ ] **Step 1: Create `whirlpool/microwave.py`**

```python
"""Abstract Microwave appliance contract (transport-agnostic)."""

from abc import ABC, abstractmethod
from enum import Enum

from .appliance import Appliance


class MicrowaveCavityState(Enum):
    Idle = "idle"
    Cooking = "cooking"
    Paused = "paused"
    Completed = "completed"
    Unknown = "unknown"


class MicrowaveDoorStatus(Enum):
    Open = "open"
    Closed = "closed"
    Unknown = "unknown"


class RecipeId(Enum):
    Microwave = "microwave"
    Reheat = "reheat"
    Defrost = "defrost"
    Soften = "soften"


class HoodFanSpeed(Enum):
    Off = "off"
    Low = "low"
    Medium = "med"
    High = "high"
    Boost = "boost"


class HoodLightLevel(Enum):
    Off = "off"
    Low = "low"
    Medium = "med"
    High = "high"


class HoodLightColor(Enum):
    WarmWhite = "warmWhite"
    NaturalWhite = "naturalWhite"
    CoolWhite = "coolWhite"


class Microwave(Appliance, ABC):
    """Public API for a microwave oven. Implementations live in transport modules."""

    # --- cavity state ---
    @abstractmethod
    def get_cavity_state(self) -> MicrowaveCavityState: ...

    @abstractmethod
    def get_door_status(self) -> MicrowaveDoorStatus: ...

    @abstractmethod
    def get_door_locked(self) -> bool | None: ...

    @abstractmethod
    def get_cavity_light(self) -> bool | None: ...

    @abstractmethod
    async def set_cavity_light(self, on: bool) -> bool: ...

    @abstractmethod
    def get_display_temperature(self) -> float | None: ...

    @abstractmethod
    def get_display_temperature_unit(self) -> str | None: ...

    @abstractmethod
    def get_turntable_enabled(self) -> bool | None: ...

    # --- cook / timer ---
    @abstractmethod
    def get_active_recipe_id(self) -> str | None: ...

    @abstractmethod
    def get_recipe_execution_state(self) -> str | None: ...

    @abstractmethod
    def get_mwo_power_level(self) -> int | None: ...

    @abstractmethod
    def get_cook_timer_state(self) -> str | None: ...

    @abstractmethod
    def get_cook_timer_total_seconds(self) -> int | None: ...

    @abstractmethod
    def get_cook_timer_remaining_seconds(self) -> int | None: ...

    @abstractmethod
    async def start_cook(
        self,
        recipe: RecipeId,
        power_level: int,
        duration_seconds: int,
    ) -> bool: ...

    @abstractmethod
    async def cancel_cook(self) -> bool: ...

    # --- hood ---
    @abstractmethod
    def get_hood_light_level(self) -> HoodLightLevel | None: ...

    @abstractmethod
    async def set_hood_light_level(self, level: HoodLightLevel) -> bool: ...

    @abstractmethod
    def get_hood_light_color(self) -> HoodLightColor | None: ...

    @abstractmethod
    async def set_hood_light_color(self, color: HoodLightColor) -> bool: ...

    @abstractmethod
    def get_hood_fan_speed(self) -> HoodFanSpeed | None: ...

    @abstractmethod
    async def set_hood_fan_speed(self, speed: HoodFanSpeed) -> bool: ...

    # --- modes ---
    @abstractmethod
    def get_remote_start_enabled(self) -> bool | None: ...

    @abstractmethod
    def get_control_locked(self) -> bool | None: ...

    @abstractmethod
    async def set_control_locked(self, on: bool) -> bool: ...

    @abstractmethod
    def get_quiet_mode(self) -> bool | None: ...

    @abstractmethod
    async def set_quiet_mode(self, on: bool) -> bool: ...

    @abstractmethod
    def get_sabbath_mode(self) -> bool | None: ...

    @abstractmethod
    async def set_sabbath_mode(self, on: bool) -> bool: ...
```

- [ ] **Step 2: Verify the ABC imports cleanly**

Run: `python -c "from whirlpool.microwave import Microwave; print(Microwave.__abstractmethods__)"`
Expected: a frozenset listing every abstract method defined above.

- [ ] **Step 3: Commit**

```bash
git add whirlpool/microwave.py
git commit -m "feat: add top-level Microwave ABC"
```

---

## Task 11: `whirlpool/httpapi/microwave.py` stub

Present purely so the facade can carry a uniform Microwave type on both sides. Never instantiated.

**Files:**
- Create: `whirlpool/httpapi/microwave.py`

- [ ] **Step 1: Create `whirlpool/httpapi/microwave.py`**

```python
"""Placeholder — legacy REST API does not support microwaves.

This module exists only so the top-level facade can typecheck against
a concrete Microwave class on the HTTP side. All abstract methods stay
abstract via inheritance, so attempting to instantiate this class
raises TypeError at runtime.
"""

from ..microwave import Microwave as MicrowaveABC


class Microwave(MicrowaveABC):
    """Not implemented. See module docstring."""
```

- [ ] **Step 2: Verify** it imports without error.

Run: `python -c "import whirlpool.httpapi.microwave"`
Expected: silent success.

- [ ] **Step 3: Commit**

```bash
git add whirlpool/httpapi/microwave.py
git commit -m "feat(httpapi): add Microwave stub for facade type consistency"
```

---

## Task 12: Slim `awsiot.Appliance` base — `deep_merge`, `_get_path*`, lifecycle

This is the foundation every AWS-side appliance class builds on. Tests use `FakeMqttClient`.

**Files:**
- Modify: `whirlpool/awsiot/appliance.py` (full rewrite)
- Create: `tests/awsiot/test_appliance_base.py`

- [ ] **Step 1: Write the failing test file**

```python
import asyncio
from typing import Any

import pytest

from whirlpool.awsiot.appliance import Appliance, deep_merge
from whirlpool.awsiot.capabilities import parse_capability_profile
from whirlpool.types import ApplianceInfo


class _ConcreteAppliance(Appliance):
    """Minimal subclass so tests can instantiate the ABC."""


@pytest.fixture
def profile(capability_mwo_raw):
    return parse_capability_profile(capability_mwo_raw)


@pytest.fixture
def info() -> ApplianceInfo:
    return ApplianceInfo(
        said="SAIDXYZ",
        name="Test MWO",
        category="cooking",
        model_number="KMMC5019JBS",
        serial_number="D1",
    )


@pytest.fixture
async def connected(fake_mqtt, profile, info) -> _ConcreteAppliance:
    await fake_mqtt.connect()
    app = _ConcreteAppliance(fake_mqtt, info, profile)
    await app.connect()
    return app


# --- deep_merge ----------------------------------------------------------

def test_deep_merge_nested_dicts():
    base = {"a": {"b": 1, "c": 2}}
    update = {"a": {"c": 3, "d": 4}}
    result = deep_merge(base, update)
    assert result == {"a": {"b": 1, "c": 3, "d": 4}}


def test_deep_merge_replaces_non_dict_leaf():
    base = {"a": 1}
    result = deep_merge(base, {"a": 2})
    assert result == {"a": 2}


def test_deep_merge_type_mismatch_keeps_existing_and_warns(
    caplog: pytest.LogCaptureFixture,
):
    base = {"a": {"nested": 1}}
    import logging

    with caplog.at_level(logging.WARNING, logger="whirlpool.awsiot.appliance"):
        deep_merge(base, {"a": "scalar"})
    assert base["a"] == {"nested": 1}
    assert any("type mismatch" in r.message.lower() for r in caplog.records)


# --- _get_path* ----------------------------------------------------------

def test_get_path_returns_none_for_missing(connected: _ConcreteAppliance):
    assert connected._get_path("primaryCavity.nonexistent") is None
    assert connected._get_path("nope") is None


def test_get_path_traverses_nested(connected: _ConcreteAppliance, state_mwo_full):
    connected._state = state_mwo_full
    assert connected._get_path_bool("primaryCavity.cavityLight") is False
    assert connected._get_path_str("primaryCavity.cavityState") == "idle"
    assert connected._get_path_int("primaryCavity.mwoPowerLevel") == 0
    assert connected._get_path_str("hoodFan.userFanSpeed") == "off"
    assert connected._get_path_str("hoodLight") == "off"


def test_get_path_type_coercion_none_on_mismatch(connected: _ConcreteAppliance):
    connected._state = {"x": "not-an-int"}
    assert connected._get_path_int("x") is None


# --- lifecycle -----------------------------------------------------------

async def test_connect_subscribes_expected_topics(
    fake_mqtt, profile, info
) -> None:
    await fake_mqtt.connect()
    app = _ConcreteAppliance(fake_mqtt, info, profile)
    await app.connect()
    model = info.model_number
    said = info.said
    cid = fake_mqtt.client_id
    expected = {
        f"cmd/{model}/{said}/response/{cid}",
        f"dt/{model}/{said}/state/update",
        f"$aws/events/presence/connected/{said}",
        f"$aws/events/presence/disconnected/{said}",
    }
    assert expected.issubset(fake_mqtt.subscriptions)


async def test_fetch_data_publishes_getstate_and_resolves_on_response(
    fake_mqtt, profile, info, state_mwo_full
) -> None:
    await fake_mqtt.connect()
    app = _ConcreteAppliance(fake_mqtt, info, profile)
    await app.connect()
    fake_mqtt.clear_published()

    async def fire_response() -> None:
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        await fake_mqtt.inject(
            f"cmd/{info.model_number}/{info.said}/response/{fake_mqtt.client_id}",
            {
                "requestId": "whatever",
                "timestamp": 1,
                "payload": state_mwo_full,
            },
        )

    task = asyncio.create_task(app.fetch_data())
    await fire_response()
    ok = await task
    assert ok is True
    assert app._state["primaryCavity"]["cavityState"] == "idle"

    # Verify getState was published on the request topic.
    request_topic = (
        f"cmd/{info.model_number}/{info.said}/request/{fake_mqtt.client_id}"
    )
    published_topics = [t for t, _ in fake_mqtt.published]
    assert request_topic in published_topics


async def test_fetch_data_times_out_returns_false(
    fake_mqtt, profile, info
) -> None:
    await fake_mqtt.connect()
    app = _ConcreteAppliance(fake_mqtt, info, profile, initial_state_timeout=0.05)
    await app.connect()
    fake_mqtt.clear_published()

    ok = await app.fetch_data()
    assert ok is False


async def test_state_delta_deep_merges(
    connected: _ConcreteAppliance, state_mwo_full, fake_mqtt, info
) -> None:
    connected._state = dict(state_mwo_full)
    # Deep-copy nested primaryCavity so later mutations don't leak.
    import copy

    connected._state = copy.deepcopy(state_mwo_full)

    await fake_mqtt.inject(
        f"dt/{info.model_number}/{info.said}/state/update",
        {"primaryCavity": {"cavityLight": True}},
    )
    assert connected._state["primaryCavity"]["cavityLight"] is True
    # Sibling keys preserved.
    assert connected._state["primaryCavity"]["doorStatus"] == "closed"
    assert connected._state["hoodFan"]["userFanSpeed"] == "off"


async def test_presence_topics_update_online(
    connected: _ConcreteAppliance, fake_mqtt, info
) -> None:
    await fake_mqtt.inject(
        f"$aws/events/presence/connected/{info.said}", {}
    )
    assert connected.get_online() is True
    await fake_mqtt.inject(
        f"$aws/events/presence/disconnected/{info.said}", {}
    )
    assert connected.get_online() is False


async def test_callback_fanout_on_state_update(
    connected: _ConcreteAppliance, fake_mqtt, info
) -> None:
    calls: list[int] = []
    connected.register_attr_callback(lambda: calls.append(1))
    await fake_mqtt.inject(
        f"dt/{info.model_number}/{info.said}/state/update",
        {"primaryCavity": {"cavityLight": True}},
    )
    assert calls == [1]


async def test_callback_exception_does_not_break_fanout(
    connected: _ConcreteAppliance, fake_mqtt, info
) -> None:
    calls: list[str] = []

    def bad() -> None:
        calls.append("bad")
        raise RuntimeError("boom")

    def good() -> None:
        calls.append("good")

    connected.register_attr_callback(bad)
    connected.register_attr_callback(good)

    await fake_mqtt.inject(
        f"dt/{info.model_number}/{info.said}/state/update", {"a": 1}
    )
    assert calls == ["bad", "good"]


async def test_send_command_builds_payload(
    connected: _ConcreteAppliance, fake_mqtt, info
) -> None:
    fake_mqtt.clear_published()
    await connected._send_command("primaryCavity", "set", cavityLight=True)

    assert len(fake_mqtt.published) == 1
    topic, payload = fake_mqtt.published[0]
    assert topic == (
        f"cmd/{info.model_number}/{info.said}/request/{fake_mqtt.client_id}"
    )
    assert payload["payload"]["addressee"] == "primaryCavity"
    assert payload["payload"]["command"] == "set"
    assert payload["payload"]["cavityLight"] is True
    assert isinstance(payload["requestId"], str)
    assert len(payload["requestId"]) >= 8
    assert isinstance(payload["timestamp"], int)


async def test_reconnect_handler_refetches_state(
    fake_mqtt, profile, info, state_mwo_full
) -> None:
    await fake_mqtt.connect()
    app = _ConcreteAppliance(fake_mqtt, info, profile)
    await app.connect()
    fake_mqtt.clear_published()

    # Simulate a disconnect then reconnect — the appliance should re-publish getState.
    await fake_mqtt.simulate_disconnect()
    await fake_mqtt.simulate_reconnect()
    await asyncio.sleep(0)
    await asyncio.sleep(0)

    request_topic = (
        f"cmd/{info.model_number}/{info.said}/request/{fake_mqtt.client_id}"
    )
    assert any(t == request_topic for t, _ in fake_mqtt.published)
```

- [ ] **Step 2: Run — expect FAIL (current appliance.py does not support this API)**

Run: `pytest tests/awsiot/test_appliance_base.py -v`
Expected: multiple failures / import errors.

- [ ] **Step 3: Replace `whirlpool/awsiot/appliance.py` with the thin base**

```python
"""Thin async MQTT-backed appliance base class.

Subclasses implement domain-level getters/setters using the protected
`_get_path_*` accessors and `_send_command` helper. All transport,
state merging, presence tracking, and reconnect handling lives here.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, override

from ..appliance import Appliance as BaseAppliance
from ..types import ApplianceInfo
from .capabilities import CapabilityProfile
from .mqttclient import MqttClient

LOGGER = logging.getLogger(__name__)

INITIAL_STATE_TIMEOUT_SECONDS = 5.0


def deep_merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge `update` into `base` in place. Returns `base`.

    When both sides have a dict at the same key, recurse. When types
    mismatch (e.g. dict vs scalar), keep the existing value and warn.
    """
    for key, new_value in update.items():
        existing = base.get(key)
        if isinstance(new_value, dict) and isinstance(existing, dict):
            deep_merge(existing, new_value)
        elif isinstance(existing, dict) and not isinstance(new_value, dict):
            LOGGER.warning(
                "deep_merge type mismatch at key %r (existing dict, update %s); "
                "keeping existing",
                key,
                type(new_value).__name__,
            )
        else:
            base[key] = new_value
    return base


class Appliance(BaseAppliance):
    """Base AWS IoT appliance."""

    def __init__(
        self,
        mqtt: MqttClient,
        appliance_info: ApplianceInfo,
        capability_profile: CapabilityProfile,
        initial_state_timeout: float = INITIAL_STATE_TIMEOUT_SECONDS,
    ) -> None:
        super().__init__(appliance_info)
        self._mqtt = mqtt
        self._capability_profile = capability_profile
        self._initial_state_timeout = initial_state_timeout

        self._state: dict[str, Any] = {}
        self._online: bool | None = None
        self._initial_state_event: asyncio.Event = asyncio.Event()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}> {self.said} | {self.name}"

    # --- public read-only ------------------------------------------------

    @property
    def capability_profile(self) -> CapabilityProfile:
        return self._capability_profile

    # --- topic builders --------------------------------------------------

    def _request_topic(self) -> str:
        return (
            f"cmd/{self.appliance_info.model_number}/{self.said}/request/"
            f"{self._mqtt.client_id}"
        )

    def _response_topic(self) -> str:
        return (
            f"cmd/{self.appliance_info.model_number}/{self.said}/response/"
            f"{self._mqtt.client_id}"
        )

    def _state_topic(self) -> str:
        return f"dt/{self.appliance_info.model_number}/{self.said}/state/update"

    def _presence_connected_topic(self) -> str:
        return f"$aws/events/presence/connected/{self.said}"

    def _presence_disconnected_topic(self) -> str:
        return f"$aws/events/presence/disconnected/{self.said}"

    # --- lifecycle -------------------------------------------------------

    async def connect(self) -> None:
        if self._mqtt.client_id is None:
            LOGGER.error("Cannot connect appliance %s: MQTT client id not set", self.said)
            return

        await self._mqtt.subscribe(self._response_topic())
        await self._mqtt.subscribe(self._state_topic())
        await self._mqtt.subscribe(self._presence_connected_topic())
        await self._mqtt.subscribe(self._presence_disconnected_topic())

        self._mqtt.add_message_handler(self._handle_mqtt_message)
        self._mqtt.add_connection_handler(on_connect=self._on_reconnect)

        await self.fetch_data()

    async def disconnect(self) -> None:
        self._mqtt.remove_message_handler(self._handle_mqtt_message)
        for topic in (
            self._response_topic(),
            self._state_topic(),
            self._presence_connected_topic(),
            self._presence_disconnected_topic(),
        ):
            await self._mqtt.unsubscribe(topic)

    @override
    async def fetch_data(self) -> bool:
        self._initial_state_event.clear()
        await self._send_command_raw(addressee="appliance", command="getState")
        try:
            await asyncio.wait_for(
                self._initial_state_event.wait(),
                timeout=self._initial_state_timeout,
            )
            return True
        except TimeoutError:
            LOGGER.warning(
                "Timed out waiting for initial state of %s", self.said
            )
            return False

    @override
    def get_online(self) -> bool | None:
        return self._online

    # --- protected helpers for subclasses --------------------------------

    def _get_path(self, path: str) -> Any | None:
        current: Any = self._state
        for part in path.split("."):
            if not isinstance(current, dict):
                return None
            current = current.get(part)
            if current is None:
                return None
        return current

    def _get_path_bool(self, path: str) -> bool | None:
        value = self._get_path(path)
        return value if isinstance(value, bool) else None

    def _get_path_int(self, path: str) -> int | None:
        value = self._get_path(path)
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        return None

    def _get_path_float(self, path: str) -> float | None:
        value = self._get_path(path)
        if isinstance(value, bool):
            return float(value)
        if isinstance(value, (int, float)):
            return float(value)
        return None

    def _get_path_str(self, path: str) -> str | None:
        value = self._get_path(path)
        return value if isinstance(value, str) else None

    async def _send_command(
        self, addressee: str, command: str, **payload_extra: Any
    ) -> None:
        await self._send_command_raw(addressee, command, **payload_extra)

    async def _send_command_raw(
        self, addressee: str, command: str, **payload_extra: Any
    ) -> None:
        if self._mqtt.client_id is None:
            LOGGER.error("Cannot send command %s on %s: MQTT not connected", command, self.said)
            return

        message: dict[str, Any] = {
            "requestId": str(uuid.uuid4()),
            "timestamp": int(time.time() * 1000),
            "payload": {
                "addressee": addressee,
                "command": command,
                **payload_extra,
            },
        }
        await self._mqtt.publish(self._request_topic(), message)

    # --- MQTT dispatch ---------------------------------------------------

    async def _handle_mqtt_message(self, topic: str, payload: dict[str, Any]) -> None:
        if topic == self._response_topic():
            body = payload.get("payload") if isinstance(payload, dict) else None
            if isinstance(body, dict):
                deep_merge(self._state, body)
                self._initial_state_event.set()
                self._fire_attr_callbacks()
            return

        if topic == self._state_topic():
            if isinstance(payload, dict):
                deep_merge(self._state, payload)
                self._fire_attr_callbacks()
            return

        if topic == self._presence_connected_topic():
            self._online = True
            self._fire_attr_callbacks()
            return

        if topic == self._presence_disconnected_topic():
            self._online = False
            self._fire_attr_callbacks()
            return

    async def _on_reconnect(self) -> None:
        try:
            await self.fetch_data()
        except Exception:
            LOGGER.exception("Failed to refetch state after reconnect for %s", self.said)

    def _fire_attr_callbacks(self) -> None:
        for cb in list(self._attr_changed):
            try:
                cb()
            except Exception:
                LOGGER.exception("attr_changed callback raised for %s", self.said)
```

- [ ] **Step 4: Run the tests — expect PASS**

Run: `pytest tests/awsiot/test_appliance_base.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Lint + type check**

Run: `ruff check whirlpool/awsiot/appliance.py tests/awsiot/test_appliance_base.py`
Run: `basedpyright whirlpool/awsiot/appliance.py`
Expected: both PASS.

- [ ] **Step 6: Commit**

```bash
git add whirlpool/awsiot/appliance.py tests/awsiot/test_appliance_base.py
git commit -m "refactor(awsiot): slim Appliance base class with deep_merge + _get_path helpers"
```

---

## Task 13: Concrete `awsiot/microwave.py`

Implements every `MicrowaveABC` method over `_get_path_*` and `_send_command`.

**Files:**
- Create: `whirlpool/awsiot/microwave.py`
- Create: `tests/awsiot/test_microwave.py`

- [ ] **Step 1: Write the failing test file**

```python
import asyncio
from typing import Any

import pytest

from whirlpool.awsiot.capabilities import parse_capability_profile
from whirlpool.awsiot.microwave import Microwave
from whirlpool.microwave import (
    HoodFanSpeed,
    HoodLightColor,
    HoodLightLevel,
    MicrowaveCavityState,
    MicrowaveDoorStatus,
    RecipeId,
)
from whirlpool.types import ApplianceInfo


@pytest.fixture
def info() -> ApplianceInfo:
    return ApplianceInfo(
        said="SAIDMWO",
        name="Test MWO",
        category="cooking",
        model_number="KMMC5019JBS",
        serial_number="D1",
    )


@pytest.fixture
def profile(capability_mwo_raw):
    return parse_capability_profile(capability_mwo_raw)


@pytest.fixture
def profile_no_hood(capability_mwo_no_hood_raw):
    return parse_capability_profile(capability_mwo_no_hood_raw)


@pytest.fixture
async def mwo(fake_mqtt, profile, info, state_mwo_full) -> Microwave:
    await fake_mqtt.connect()
    app = Microwave(fake_mqtt, info, profile)
    await app.connect()
    # Seed state directly for getter tests.
    import copy
    app._state = copy.deepcopy(state_mwo_full)
    return app


# --- getters -------------------------------------------------------------

def test_cavity_state_idle(mwo: Microwave):
    assert mwo.get_cavity_state() == MicrowaveCavityState.Idle


def test_cavity_state_cooking(mwo: Microwave, state_mwo_cooking):
    import copy
    mwo._state = copy.deepcopy(state_mwo_cooking)
    assert mwo.get_cavity_state() == MicrowaveCavityState.Cooking


def test_cavity_state_unknown_for_unrecognized(mwo: Microwave):
    mwo._state["primaryCavity"]["cavityState"] = "???"
    assert mwo.get_cavity_state() == MicrowaveCavityState.Unknown


def test_door_status(mwo: Microwave):
    assert mwo.get_door_status() == MicrowaveDoorStatus.Closed


def test_cavity_light(mwo: Microwave):
    assert mwo.get_cavity_light() is False


def test_mwo_power_level(mwo: Microwave, state_mwo_cooking):
    import copy
    mwo._state = copy.deepcopy(state_mwo_cooking)
    assert mwo.get_mwo_power_level() == 80


def test_cook_timer_total_and_remaining(mwo: Microwave, state_mwo_cooking):
    import copy
    mwo._state = copy.deepcopy(state_mwo_cooking)
    assert mwo.get_cook_timer_total_seconds() == 30
    # Remaining may be negative when timeComplete is in the past —
    # the getter clamps to >= 0.
    remaining = mwo.get_cook_timer_remaining_seconds()
    assert remaining is None or remaining >= 0


def test_hood_fan_speed(mwo: Microwave):
    assert mwo.get_hood_fan_speed() == HoodFanSpeed.Off


def test_hood_light_level(mwo: Microwave):
    assert mwo.get_hood_light_level() == HoodLightLevel.Off


def test_hood_light_color(mwo: Microwave):
    assert mwo.get_hood_light_color() == HoodLightColor.WarmWhite


def test_remote_start_enabled(mwo: Microwave):
    assert mwo.get_remote_start_enabled() is True


def test_control_locked(mwo: Microwave):
    assert mwo.get_control_locked() is False


# --- setters -------------------------------------------------------------

async def test_set_cavity_light_publishes_command(mwo: Microwave, fake_mqtt):
    fake_mqtt.clear_published()
    ok = await mwo.set_cavity_light(True)
    assert ok is True
    _, payload = fake_mqtt.published[-1]
    assert payload["payload"]["addressee"] == "primaryCavity"
    assert payload["payload"]["command"] == "set"
    assert payload["payload"]["cavityLight"] is True


async def test_set_hood_fan_speed_publishes_command(mwo: Microwave, fake_mqtt):
    fake_mqtt.clear_published()
    ok = await mwo.set_hood_fan_speed(HoodFanSpeed.High)
    assert ok is True
    _, payload = fake_mqtt.published[-1]
    assert payload["payload"]["addressee"] == "hoodFan"
    assert payload["payload"]["command"] == "set"
    assert payload["payload"]["value"] == "high"


async def test_set_hood_light_level(mwo: Microwave, fake_mqtt):
    fake_mqtt.clear_published()
    await mwo.set_hood_light_level(HoodLightLevel.Medium)
    _, payload = fake_mqtt.published[-1]
    assert payload["payload"]["addressee"] == "hoodLight"
    assert payload["payload"]["command"] == "set"
    assert payload["payload"]["value"] == "med"


async def test_set_hood_light_color(mwo: Microwave, fake_mqtt):
    fake_mqtt.clear_published()
    await mwo.set_hood_light_color(HoodLightColor.CoolWhite)
    _, payload = fake_mqtt.published[-1]
    assert payload["payload"]["addressee"] == "hoodLightColor"
    assert payload["payload"]["command"] == "set"
    assert payload["payload"]["value"] == "coolWhite"


async def test_set_quiet_mode(mwo: Microwave, fake_mqtt):
    fake_mqtt.clear_published()
    await mwo.set_quiet_mode(True)
    _, payload = fake_mqtt.published[-1]
    assert payload["payload"]["addressee"] == "appliance"
    assert payload["payload"]["command"] == "set"
    assert payload["payload"]["quietMode"] is True


# --- start_cook validation -----------------------------------------------

async def test_start_cook_happy_path(mwo: Microwave, fake_mqtt):
    fake_mqtt.clear_published()
    ok = await mwo.start_cook(RecipeId.Microwave, 80, 30)
    assert ok is True
    _, payload = fake_mqtt.published[-1]
    body = payload["payload"]
    assert body["addressee"] == "primaryCavity"
    assert body["command"] == "run"
    assert body["recipeID"] == "microwave"
    assert body["mwoPowerLevel"] == 80.0
    assert body["cookTimer"] == {"command": "start", "time": 30}


async def test_start_cook_invalid_power_raises(mwo: Microwave):
    with pytest.raises(ValueError):
        await mwo.start_cook(RecipeId.Microwave, 0, 30)
    with pytest.raises(ValueError):
        await mwo.start_cook(RecipeId.Microwave, 101, 30)


async def test_start_cook_invalid_duration_raises(mwo: Microwave):
    with pytest.raises(ValueError):
        await mwo.start_cook(RecipeId.Microwave, 50, 0)


async def test_start_cook_requires_remote_start(
    mwo: Microwave, fake_mqtt, caplog: pytest.LogCaptureFixture
):
    mwo._state["remoteStartEnable"] = False
    fake_mqtt.clear_published()
    import logging

    with caplog.at_level(logging.WARNING, logger="whirlpool.awsiot.microwave"):
        ok = await mwo.start_cook(RecipeId.Microwave, 50, 30)
    assert ok is False
    assert fake_mqtt.published == []


async def test_cancel_cook(mwo: Microwave, fake_mqtt):
    fake_mqtt.clear_published()
    ok = await mwo.cancel_cook()
    assert ok is True
    _, payload = fake_mqtt.published[-1]
    assert payload["payload"]["addressee"] == "primaryCavity"
    assert payload["payload"]["command"] == "cancel"


# --- hood feature gating -------------------------------------------------

async def test_hood_fan_getter_returns_none_when_absent(
    fake_mqtt, profile_no_hood, info
):
    await fake_mqtt.connect()
    app = Microwave(fake_mqtt, info, profile_no_hood)
    await app.connect()
    app._state = {"primaryCavity": {"cavityState": "idle"}}
    assert app.get_hood_fan_speed() is None


async def test_hood_fan_setter_skipped_when_feature_absent(
    fake_mqtt, profile_no_hood, info, caplog: pytest.LogCaptureFixture
):
    await fake_mqtt.connect()
    app = Microwave(fake_mqtt, info, profile_no_hood)
    await app.connect()
    fake_mqtt.clear_published()

    import logging

    with caplog.at_level(logging.WARNING, logger="whirlpool.awsiot.microwave"):
        ok = await app.set_hood_fan_speed(HoodFanSpeed.High)
    assert ok is False
    assert fake_mqtt.published == []


# --- state delta merge --------------------------------------------------

async def test_state_delta_flips_cavity_light(mwo: Microwave, fake_mqtt, info):
    await fake_mqtt.inject(
        f"dt/{info.model_number}/{info.said}/state/update",
        {"primaryCavity": {"cavityLight": True}},
    )
    assert mwo.get_cavity_light() is True
    assert mwo.get_door_status() == MicrowaveDoorStatus.Closed  # untouched
```

- [ ] **Step 2: Run — expect FAIL (`awsiot.microwave` does not exist)**

Run: `pytest tests/awsiot/test_microwave.py -v`
Expected: ImportError.

- [ ] **Step 3: Create `whirlpool/awsiot/microwave.py`**

```python
"""Concrete awsiot Microwave — translates MQTT state to MicrowaveABC."""

from __future__ import annotations

import logging
import time
from typing import override

from ..microwave import (
    HoodFanSpeed,
    HoodLightColor,
    HoodLightLevel,
    Microwave as MicrowaveABC,
    MicrowaveCavityState,
    MicrowaveDoorStatus,
    RecipeId,
)
from .appliance import Appliance
from .factory import register_appliance
from .matchers import all_of, has_addressee, has_feature

LOGGER = logging.getLogger(__name__)

_CAVITY_STATE_MAP: dict[str, MicrowaveCavityState] = {
    "idle": MicrowaveCavityState.Idle,
    "cooking": MicrowaveCavityState.Cooking,
    "paused": MicrowaveCavityState.Paused,
    "completed": MicrowaveCavityState.Completed,
}

_DOOR_STATUS_MAP: dict[str, MicrowaveDoorStatus] = {
    "open": MicrowaveDoorStatus.Open,
    "closed": MicrowaveDoorStatus.Closed,
}

_HOOD_FAN_MAP: dict[str, HoodFanSpeed] = {e.value: e for e in HoodFanSpeed}
_HOOD_LIGHT_MAP: dict[str, HoodLightLevel] = {e.value: e for e in HoodLightLevel}
_HOOD_LIGHT_COLOR_MAP: dict[str, HoodLightColor] = {
    e.value: e for e in HoodLightColor
}


@register_appliance(
    matcher=all_of(
        has_addressee("primaryCavity"),
        has_feature("microwaveOven"),
    ),
    priority=10,
)
class Microwave(Appliance, MicrowaveABC):
    # --- cavity state ----------------------------------------------------

    @override
    def get_cavity_state(self) -> MicrowaveCavityState:
        raw = self._get_path_str("primaryCavity.cavityState")
        if raw is None:
            return MicrowaveCavityState.Unknown
        return _CAVITY_STATE_MAP.get(raw, MicrowaveCavityState.Unknown)

    @override
    def get_door_status(self) -> MicrowaveDoorStatus:
        raw = self._get_path_str("primaryCavity.doorStatus")
        if raw is None:
            return MicrowaveDoorStatus.Unknown
        return _DOOR_STATUS_MAP.get(raw, MicrowaveDoorStatus.Unknown)

    @override
    def get_door_locked(self) -> bool | None:
        raw = self._get_path_str("primaryCavity.doorLockStatus")
        if raw is None:
            return None
        return raw == "locked"

    @override
    def get_cavity_light(self) -> bool | None:
        return self._get_path_bool("primaryCavity.cavityLight")

    @override
    async def set_cavity_light(self, on: bool) -> bool:
        await self._send_command("primaryCavity", "set", cavityLight=on)
        return True

    @override
    def get_display_temperature(self) -> float | None:
        return self._get_path_float("primaryCavity.ovenDisplayTemperature")

    @override
    def get_display_temperature_unit(self) -> str | None:
        raw = self._get_path_str("temperatureUnit")
        if raw is None:
            return None
        return "F" if raw.lower().startswith("f") else "C"

    @override
    def get_turntable_enabled(self) -> bool | None:
        raw = self._get_path_str("primaryCavity.turnTable")
        if raw is None:
            return None
        return raw == "enabled"

    # --- cook / timer ----------------------------------------------------

    @override
    def get_active_recipe_id(self) -> str | None:
        raw = self._get_path_str("primaryCavity.recipeId")
        return raw or None

    @override
    def get_recipe_execution_state(self) -> str | None:
        return self._get_path_str("primaryCavity.recipeExecutionState")

    @override
    def get_mwo_power_level(self) -> int | None:
        return self._get_path_int("primaryCavity.mwoPowerLevel")

    @override
    def get_cook_timer_state(self) -> str | None:
        return self._get_path_str("primaryCavity.cookTimer.state")

    @override
    def get_cook_timer_total_seconds(self) -> int | None:
        return self._get_path_int("primaryCavity.cookTimer.time")

    @override
    def get_cook_timer_remaining_seconds(self) -> int | None:
        time_complete = self._get_path_int("primaryCavity.cookTimer.timeComplete")
        if time_complete is None:
            return self._get_path_int("primaryCavity.cookTimer.time")
        remaining = time_complete - int(time.time())
        return max(0, remaining)

    @override
    async def start_cook(
        self,
        recipe: RecipeId,
        power_level: int,
        duration_seconds: int,
    ) -> bool:
        if not 1 <= power_level <= 100:
            raise ValueError("power_level must be between 1 and 100")
        if duration_seconds < 1:
            raise ValueError("duration_seconds must be >= 1")
        if not self.get_remote_start_enabled():
            LOGGER.warning(
                "Remote start is not enabled on %s — enable on the physical panel",
                self.said,
            )
            return False
        await self._send_command(
            "primaryCavity",
            "run",
            recipeID=recipe.value,
            mwoPowerLevel=float(power_level),
            cookTimer={"command": "start", "time": duration_seconds},
        )
        return True

    @override
    async def cancel_cook(self) -> bool:
        await self._send_command("primaryCavity", "cancel")
        return True

    # --- hood ------------------------------------------------------------

    @override
    def get_hood_fan_speed(self) -> HoodFanSpeed | None:
        raw = self._get_path_str("hoodFan.userFanSpeed")
        return _HOOD_FAN_MAP.get(raw) if raw else None

    @override
    async def set_hood_fan_speed(self, speed: HoodFanSpeed) -> bool:
        if not self._capability_profile.has_addressee("hoodFan"):
            LOGGER.warning("Model %s has no hood fan", self.said)
            return False
        await self._send_command("hoodFan", "set", value=speed.value)
        return True

    @override
    def get_hood_light_level(self) -> HoodLightLevel | None:
        raw = self._get_path_str("hoodLight")
        return _HOOD_LIGHT_MAP.get(raw) if raw else None

    @override
    async def set_hood_light_level(self, level: HoodLightLevel) -> bool:
        if not self._capability_profile.has_addressee("hoodLight"):
            LOGGER.warning("Model %s has no hood light", self.said)
            return False
        await self._send_command("hoodLight", "set", value=level.value)
        return True

    @override
    def get_hood_light_color(self) -> HoodLightColor | None:
        raw = self._get_path_str("hoodLightColor")
        return _HOOD_LIGHT_COLOR_MAP.get(raw) if raw else None

    @override
    async def set_hood_light_color(self, color: HoodLightColor) -> bool:
        if not self._capability_profile.has_addressee("hoodLightColor"):
            LOGGER.warning("Model %s has no hood light color control", self.said)
            return False
        await self._send_command("hoodLightColor", "set", value=color.value)
        return True

    # --- modes -----------------------------------------------------------

    @override
    def get_remote_start_enabled(self) -> bool | None:
        return self._get_path_bool("remoteStartEnable")

    @override
    def get_control_locked(self) -> bool | None:
        return self._get_path_bool("hmiControlLockout")

    @override
    async def set_control_locked(self, on: bool) -> bool:
        await self._send_command("appliance", "set", hmiControlLockout=on)
        return True

    @override
    def get_quiet_mode(self) -> bool | None:
        return self._get_path_bool("quietMode")

    @override
    async def set_quiet_mode(self, on: bool) -> bool:
        await self._send_command("appliance", "set", quietMode=on)
        return True

    @override
    def get_sabbath_mode(self) -> bool | None:
        return self._get_path_bool("sabbathMode")

    @override
    async def set_sabbath_mode(self, on: bool) -> bool:
        await self._send_command("appliance", "set", sabbathMode=on)
        return True
```

- [ ] **Step 4: Run tests — expect PASS**

Run: `pytest tests/awsiot/test_microwave.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Lint + typecheck**

Run: `ruff check whirlpool/awsiot/microwave.py tests/awsiot/test_microwave.py`
Run: `basedpyright whirlpool/awsiot/microwave.py`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add whirlpool/awsiot/microwave.py tests/awsiot/test_microwave.py
git commit -m "feat(awsiot): implement Microwave for KitchenAid MWO"
```

---

## Task 14: AWS-side category stubs (Oven, Aircon, Dryer, Washer, Refrigerator)

Each stub is ~15 lines, inherits from both `Appliance` and the corresponding top-level ABC, registers with the factory, and relies on ABC inheritance to raise `TypeError` on instantiation (since the abstract methods are unimplemented). Stub priorities are lower than Microwave's priority of 10.

**Files:**
- Create: `whirlpool/awsiot/oven.py`
- Create: `whirlpool/awsiot/aircon.py`
- Create: `whirlpool/awsiot/dryer.py`
- Create: `whirlpool/awsiot/washer.py`
- Create: `whirlpool/awsiot/refrigerator.py`

- [ ] **Step 1: Create `whirlpool/awsiot/oven.py`**

```python
"""Stub AWS-side Oven.

Contributors: fill in the Oven ABC methods using the `_get_path_*` and
`_send_command` helpers on `Appliance`, then add a test file mirroring
`test_microwave.py`. The matcher is intentionally narrower than
Microwave's: ovens have `primaryCavity` but do NOT carry the
`microwaveOven` feature.
"""

from ..oven import Oven as OvenABC
from .appliance import Appliance
from .factory import register_appliance
from .matchers import all_of, has_addressee, has_feature, not_


@register_appliance(
    matcher=all_of(
        has_addressee("primaryCavity"),
        not_(has_feature("microwaveOven")),
    ),
    priority=5,
)
class Oven(Appliance, OvenABC):
    """Stub — abstract methods are unimplemented and raise at instantiation."""
```

- [ ] **Step 2: Create `whirlpool/awsiot/aircon.py`**

```python
"""Stub AWS-side Aircon. See awsiot/oven.py for the contributor pattern."""

from ..aircon import Aircon as AirconABC
from .appliance import Appliance
from .factory import register_appliance
from .matchers import thing_category


@register_appliance(matcher=thing_category("airconditioner"), priority=5)
class Aircon(Appliance, AirconABC):
    """Stub — see module docstring."""
```

- [ ] **Step 3: Create `whirlpool/awsiot/dryer.py`**

```python
"""Stub AWS-side Dryer. See awsiot/oven.py for the contributor pattern."""

from ..dryer import Dryer as DryerABC
from .appliance import Appliance
from .factory import register_appliance
from .matchers import any_of, thing_category, has_feature


@register_appliance(
    matcher=any_of(thing_category("laundry"), has_feature("dryer")),
    priority=4,
)
class Dryer(Appliance, DryerABC):
    """Stub — see module docstring."""
```

- [ ] **Step 4: Create `whirlpool/awsiot/washer.py`**

```python
"""Stub AWS-side Washer. See awsiot/oven.py for the contributor pattern."""

from ..washer import Washer as WasherABC
from .appliance import Appliance
from .factory import register_appliance
from .matchers import any_of, thing_category, has_feature


@register_appliance(
    matcher=any_of(thing_category("fabriccare"), has_feature("washer")),
    priority=5,
)
class Washer(Appliance, WasherABC):
    """Stub — see module docstring."""
```

- [ ] **Step 5: Create `whirlpool/awsiot/refrigerator.py`**

```python
"""Stub AWS-side Refrigerator. See awsiot/oven.py for the contributor pattern."""

from ..refrigerator import Refrigerator as RefrigeratorABC
from .appliance import Appliance
from .factory import register_appliance
from .matchers import thing_category


@register_appliance(matcher=thing_category("refrigerator"), priority=5)
class Refrigerator(Appliance, RefrigeratorABC):
    """Stub — see module docstring."""
```

- [ ] **Step 6: Verify stubs import cleanly and register with the factory**

Run: `python -c "import whirlpool.awsiot.oven, whirlpool.awsiot.aircon, whirlpool.awsiot.dryer, whirlpool.awsiot.washer, whirlpool.awsiot.refrigerator; from whirlpool.awsiot.factory import DEFAULT_FACTORY; print(len(DEFAULT_FACTORY._registrations))"`
Expected: a positive integer (exact number depends on what else is imported, but >= 5).

- [ ] **Step 7: Lint**

Run: `ruff check whirlpool/awsiot/oven.py whirlpool/awsiot/aircon.py whirlpool/awsiot/dryer.py whirlpool/awsiot/washer.py whirlpool/awsiot/refrigerator.py`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add whirlpool/awsiot/oven.py whirlpool/awsiot/aircon.py whirlpool/awsiot/dryer.py whirlpool/awsiot/washer.py whirlpool/awsiot/refrigerator.py
git commit -m "feat(awsiot): add category stubs for contributor templates"
```

---

## Task 15: Refactor `awsiot/appliancesmanager.py` to use factory + capability download

The manager now:
- Creates one `CapabilityDownloader` for the session.
- For each thing, downloads the capability, runs it through the factory, calls `appliance.connect()`, and registers by ABC.
- Has per-appliance error isolation (try/except around each `_add_appliance` call).
- Drops the `asyncio.sleep(5)` TODO.
- Exposes a `microwaves` property.

**Files:**
- Modify: `whirlpool/awsiot/appliancesmanager.py`
- Create: `tests/awsiot/test_appliancesmanager.py`

- [ ] **Step 1: Write the failing test file**

```python
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest

from whirlpool.awsiot.appliancesmanager import AppliancesManager
from whirlpool.awsiot.capabilities import CapabilityProfile, parse_capability_profile
from whirlpool.microwave import Microwave as MicrowaveABC


class _NoopAuth:
    async def do_auth(self, _refresh: bool = False) -> None:
        return None


class _FakeWhirlpoolAuth:
    async def get_access_token(self) -> str | None:
        return "token"


@pytest.fixture
def patched_manager(
    fake_mqtt, capability_mwo_raw, thing_mwo, state_mwo_full
):
    """Patch AppliancesManager's MQTT client, Things, and downloader."""

    async def fake_connect() -> bool:
        await fake_mqtt.connect()
        return True

    async def fake_disconnect() -> None:
        await fake_mqtt.disconnect()

    things_return: list[dict[str, Any]] = [thing_mwo]

    class _FakeThings:
        def __init__(self, *args, **kwargs):
            pass

        async def list_things(self) -> list[dict[str, Any]]:
            return list(things_return)

    async def fake_download(
        self, said: str, model: str, part: str
    ) -> CapabilityProfile:
        return parse_capability_profile(capability_mwo_raw)

    async def fake_fetch_data(self) -> bool:
        # Seed state directly, skipping MQTT round-trip.
        import copy
        self._state = copy.deepcopy(state_mwo_full)
        self._initial_state_event.set()
        return True

    with (
        patch("whirlpool.awsiot.appliancesmanager.Things", _FakeThings),
        patch(
            "whirlpool.awsiot.appliancesmanager.MqttClient",
            return_value=fake_mqtt,
        ),
        patch(
            "whirlpool.awsiot.capabilities.CapabilityDownloader.get",
            fake_download,
        ),
        patch(
            "whirlpool.awsiot.appliance.Appliance.fetch_data",
            fake_fetch_data,
        ),
    ):
        yield things_return


async def test_connect_registers_microwave(
    patched_manager, fake_mqtt, client_session_fixture
):
    # Ensure Microwave registration is loaded before factory build.
    import whirlpool.awsiot.microwave  # noqa: F401

    manager = AppliancesManager(
        _FakeWhirlpoolAuth(), client_session_fixture, lambda: None
    )
    ok = await manager.connect()
    assert ok is True
    assert len(manager.microwaves) == 1
    assert isinstance(manager.microwaves[0], MicrowaveABC)


async def test_connect_with_empty_things_still_succeeds(
    patched_manager, client_session_fixture
):
    patched_manager.clear()
    manager = AppliancesManager(
        _FakeWhirlpoolAuth(), client_session_fixture, lambda: None
    )
    ok = await manager.connect()
    assert ok is True
    assert manager.microwaves == []


async def test_thing_without_capability_part_number_is_skipped(
    patched_manager, client_session_fixture, thing_mwo
):
    broken = dict(thing_mwo)
    broken["attributes"] = dict(thing_mwo["attributes"])
    broken["attributes"].pop("CapabilityPartNumber")
    patched_manager.clear()
    patched_manager.append(broken)

    manager = AppliancesManager(
        _FakeWhirlpoolAuth(), client_session_fixture, lambda: None
    )
    ok = await manager.connect()
    assert ok is True
    assert manager.microwaves == []


async def test_one_failing_appliance_does_not_abort_others(
    patched_manager, client_session_fixture, thing_mwo, capability_mwo_raw
):
    import whirlpool.awsiot.microwave  # noqa: F401
    from whirlpool.awsiot.capabilities import (
        CapabilityDownloadError,
        parse_capability_profile,
    )

    second = dict(thing_mwo)
    second["thingName"] = "SECOND"
    patched_manager.append(second)

    calls: list[str] = []

    async def selective_download(
        self, said: str, model: str, part: str
    ) -> CapabilityProfile:
        calls.append(said)
        if said == thing_mwo["thingName"]:
            raise CapabilityDownloadError("boom")
        return parse_capability_profile(capability_mwo_raw)

    with patch(
        "whirlpool.awsiot.capabilities.CapabilityDownloader.get",
        selective_download,
    ):
        manager = AppliancesManager(
            _FakeWhirlpoolAuth(), client_session_fixture, lambda: None
        )
        ok = await manager.connect()
    assert ok is True
    # Second one should have been registered despite the first's failure.
    assert any(m.said == "SECOND" for m in manager.microwaves)
```

- [ ] **Step 2: Run — expect FAIL (old manager uses old APIs, doesn't expose `microwaves`, etc.)**

Run: `pytest tests/awsiot/test_appliancesmanager.py -v`
Expected: multiple failures.

- [ ] **Step 3: Rewrite `whirlpool/awsiot/appliancesmanager.py`**

```python
"""AWS IoT appliances manager: MQTT + capability download + factory."""

from __future__ import annotations

import logging
from collections.abc import Callable
from functools import cached_property
from typing import Any

import aiohttp

# Import subclass modules for side-effect factory registration.
from . import aircon as _aircon  # noqa: F401
from . import dryer as _dryer  # noqa: F401
from . import microwave as _microwave  # noqa: F401
from . import oven as _oven  # noqa: F401
from . import refrigerator as _refrigerator  # noqa: F401
from . import washer as _washer  # noqa: F401
from ..aircon import Aircon as AirconABC
from ..auth import Auth as WhirlpoolAuth
from ..dryer import Dryer as DryerABC
from ..microwave import Microwave as MicrowaveABC
from ..oven import Oven as OvenABC
from ..refrigerator import Refrigerator as RefrigeratorABC
from ..types import ApplianceInfo
from ..washer import Washer as WasherABC
from .appliance import Appliance
from .auth import Auth, AuthException
from .capabilities import (
    CapabilityDownloadError,
    CapabilityDownloader,
)
from .factory import DEFAULT_FACTORY
from .mqttclient import MqttClient
from .things import Things

LOGGER = logging.getLogger(__name__)


class AppliancesManager:
    def __init__(
        self,
        whirlpool_auth: WhirlpoolAuth,
        session: aiohttp.ClientSession,
        appliances_update_callback: Callable[[], None],
    ) -> None:
        self._whirlpool_auth = whirlpool_auth
        self._session = session
        self._update_callback = appliances_update_callback

        self._aws_auth = Auth(self._whirlpool_auth, self._session)
        self._mqtt = MqttClient(self._aws_auth)
        self._capability_downloader = CapabilityDownloader(
            self._mqtt, self._session
        )

        self._aircons: dict[str, Appliance] = {}
        self._dryers: dict[str, Appliance] = {}
        self._washers: dict[str, Appliance] = {}
        self._ovens: dict[str, Appliance] = {}
        self._refrigerators: dict[str, Appliance] = {}
        self._microwaves: dict[str, Appliance] = {}

    # --- category properties --------------------------------------------

    @cached_property
    def all_appliances(self) -> dict[str, Appliance]:
        return {
            **self._aircons,
            **self._dryers,
            **self._washers,
            **self._ovens,
            **self._refrigerators,
            **self._microwaves,
        }

    @property
    def aircons(self) -> list[AirconABC]:
        return list(self._aircons.values())  # type: ignore[return-value]

    @property
    def dryers(self) -> list[DryerABC]:
        return list(self._dryers.values())  # type: ignore[return-value]

    @property
    def washers(self) -> list[WasherABC]:
        return list(self._washers.values())  # type: ignore[return-value]

    @property
    def ovens(self) -> list[OvenABC]:
        return list(self._ovens.values())  # type: ignore[return-value]

    @property
    def refrigerators(self) -> list[RefrigeratorABC]:
        return list(self._refrigerators.values())  # type: ignore[return-value]

    @property
    def microwaves(self) -> list[MicrowaveABC]:
        return list(self._microwaves.values())  # type: ignore[return-value]

    # --- lifecycle -------------------------------------------------------

    async def connect(self) -> bool:
        try:
            if not await self._mqtt.connect():
                LOGGER.error("Failed to connect to MQTT broker")
                return False

            things = await Things(self._aws_auth, self._session).list_things()
        except AuthException as e:
            LOGGER.error("AWS auth failed: %s", e)
            return False
        except Exception:
            LOGGER.exception("Unexpected error during AWS connect")
            return False

        if not things:
            LOGGER.info("No AWS IoT things for this account")
            return True

        for thing in things:
            try:
                await self._add_appliance(thing)
            except Exception:
                LOGGER.exception(
                    "Failed to add AWS appliance %s", thing.get("thingName")
                )
                continue

        return True

    async def disconnect(self) -> None:
        for app in list(self.all_appliances.values()):
            try:
                await app.disconnect()
            except Exception:
                LOGGER.exception("Error disconnecting %s", app.said)
        await self._mqtt.disconnect()

    # --- helpers ---------------------------------------------------------

    async def _add_appliance(self, thing: dict[str, Any]) -> None:
        info = self._build_info(thing)
        attrs = thing.get("attributes") or {}
        cap_part_number = attrs.get("CapabilityPartNumber")
        if not cap_part_number:
            LOGGER.warning(
                "Thing %s has no CapabilityPartNumber; cannot route", info.said
            )
            return

        try:
            profile = await self._capability_downloader.get(
                info.said, info.model_number, cap_part_number
            )
        except CapabilityDownloadError:
            LOGGER.exception(
                "Capability download failed for %s (%s)",
                info.said,
                cap_part_number,
            )
            return

        appliance = DEFAULT_FACTORY.build(self._mqtt, profile, thing, info)
        if appliance is None:
            LOGGER.warning(
                "No AWS appliance class matches %s "
                "(category=%s, addressees=%s, features=%s)",
                info.said,
                info.category,
                sorted(profile.addressees),
                sorted(profile.features),
            )
            return

        await appliance.connect()
        self._register(appliance)

    def _register(self, appliance: Appliance) -> None:
        if isinstance(appliance, MicrowaveABC):
            self._microwaves[appliance.said] = appliance
        elif isinstance(appliance, OvenABC):
            self._ovens[appliance.said] = appliance
        elif isinstance(appliance, AirconABC):
            self._aircons[appliance.said] = appliance
        elif isinstance(appliance, DryerABC):
            self._dryers[appliance.said] = appliance
        elif isinstance(appliance, WasherABC):
            self._washers[appliance.said] = appliance
        elif isinstance(appliance, RefrigeratorABC):
            self._refrigerators[appliance.said] = appliance
        else:
            LOGGER.warning(
                "Built appliance %s does not inherit any known ABC; ignoring",
                appliance.said,
            )
            return

        self.__dict__.pop("all_appliances", None)
        self._update_callback()

    def _build_info(self, thing: dict[str, Any]) -> ApplianceInfo:
        attrs = thing.get("attributes") or {}
        raw_name = attrs.get("Name", "")
        try:
            name = bytes.fromhex(raw_name).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            name = thing.get("thingName", "")
        return ApplianceInfo(
            said=thing.get("thingName", ""),
            name=name,
            category=str(attrs.get("Category", "")).lower(),
            model_number=thing.get("thingTypeName", ""),
            serial_number=attrs.get("Serial", ""),
        )
```

- [ ] **Step 4: Run the tests — expect PASS**

Run: `pytest tests/awsiot/test_appliancesmanager.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Lint + typecheck**

Run: `ruff check whirlpool/awsiot/appliancesmanager.py tests/awsiot/test_appliancesmanager.py`
Run: `basedpyright whirlpool/awsiot/appliancesmanager.py`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add whirlpool/awsiot/appliancesmanager.py tests/awsiot/test_appliancesmanager.py
git commit -m "refactor(awsiot): rewrite AppliancesManager to use factory + capability download"
```

---

## Task 16: Facade `AppliancesManager.microwaves` property and HTTP manager symmetry

Top-level facade and HTTP manager gain a `microwaves` property for API consistency. HTTP always returns `[]`.

**Files:**
- Modify: `whirlpool/appliancesmanager.py`
- Modify: `whirlpool/httpapi/appliancesmanager.py`

- [ ] **Step 1: Open `whirlpool/httpapi/appliancesmanager.py` and add `_microwaves` + property**

In `HttpAppliancesManager.__init__`, after `self._refrigerators: dict[str, Any] = {}`, add:

```python
        self._microwaves: dict[str, Any] = {}
```

After the `refrigerators` property definition (the last per-category property), add:

```python
    @property
    def microwaves(self) -> list:
        return list(self._microwaves.values())
```

Also update the `all_appliances` `cached_property` to include `**self._microwaves` alongside the existing categories:

```python
    @cached_property
    def all_appliances(self) -> dict[str, Appliance]:
        return {
            **self._aircons,
            **self._dryers,
            **self._washers,
            **self._ovens,
            **self._refrigerators,
            **self._microwaves,
        }
```

- [ ] **Step 2: Open `whirlpool/appliancesmanager.py` and add `microwaves` to the facade**

Add this import at the top, grouped with existing device imports:

```python
from .microwave import Microwave
```

After the `refrigerators` property definition, add:

```python
    # TODO: use cached_property
    @property
    def microwaves(self) -> list[Microwave]:
        return (
            self._http_appliances_manager.microwaves
            + self._aws_appliances_manager.microwaves
        )
```

- [ ] **Step 3: Run the full test suite**

Run: `pytest -x`
Expected: no regressions. Existing tests that check `all_appliances` unchanged; new `microwaves` path verified by `tests/awsiot/test_appliancesmanager.py`.

- [ ] **Step 4: Lint + typecheck**

Run: `ruff check whirlpool/appliancesmanager.py whirlpool/httpapi/appliancesmanager.py`
Run: `basedpyright whirlpool/appliancesmanager.py whirlpool/httpapi/appliancesmanager.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add whirlpool/appliancesmanager.py whirlpool/httpapi/appliancesmanager.py
git commit -m "feat: expose microwaves on facade and http manager"
```

---

## Task 17: Integration test — full chain with `FakeMqttClient`

**Files:**
- Create: `tests/awsiot/test_integration_microwave.py`

- [ ] **Step 1: Write the test**

```python
import asyncio
import copy
from typing import Any
from unittest.mock import patch

import pytest

from whirlpool.awsiot.appliancesmanager import AppliancesManager
from whirlpool.awsiot.capabilities import CapabilityProfile, parse_capability_profile
from whirlpool.microwave import HoodFanSpeed, RecipeId
from whirlpool.microwave import Microwave as MicrowaveABC


class _FakeWhirlpoolAuth:
    async def get_access_token(self) -> str | None:
        return "token"


async def test_full_chain_start_and_state_update(
    fake_mqtt,
    client_session_fixture,
    capability_mwo_raw,
    thing_mwo,
    state_mwo_full,
):
    import whirlpool.awsiot.microwave  # noqa: F401

    async def fake_fetch(self) -> bool:
        self._state = copy.deepcopy(state_mwo_full)
        self._initial_state_event.set()
        return True

    async def fake_download(self, said, model, part) -> CapabilityProfile:
        return parse_capability_profile(capability_mwo_raw)

    class _FakeThings:
        def __init__(self, *args, **kwargs):
            pass

        async def list_things(self) -> list[dict[str, Any]]:
            return [thing_mwo]

    with (
        patch("whirlpool.awsiot.appliancesmanager.Things", _FakeThings),
        patch(
            "whirlpool.awsiot.appliancesmanager.MqttClient",
            return_value=fake_mqtt,
        ),
        patch(
            "whirlpool.awsiot.capabilities.CapabilityDownloader.get",
            fake_download,
        ),
        patch(
            "whirlpool.awsiot.appliance.Appliance.fetch_data",
            fake_fetch,
        ),
    ):
        manager = AppliancesManager(
            _FakeWhirlpoolAuth(), client_session_fixture, lambda: None
        )
        ok = await manager.connect()
    assert ok is True

    assert len(manager.microwaves) == 1
    mwo = manager.microwaves[0]
    assert isinstance(mwo, MicrowaveABC)

    # Callback fanout.
    updates: list[int] = []
    mwo.register_attr_callback(lambda: updates.append(1))

    # State delta arrives: cooking transition.
    state_topic = (
        f"dt/{thing_mwo['thingTypeName']}/{thing_mwo['thingName']}/state/update"
    )
    await fake_mqtt.inject(
        state_topic,
        {"primaryCavity": {"cavityState": "cooking"}},
    )
    from whirlpool.microwave import MicrowaveCavityState
    assert mwo.get_cavity_state() == MicrowaveCavityState.Cooking
    assert updates == [1]

    # Command path.
    fake_mqtt.clear_published()
    ok = await mwo.set_hood_fan_speed(HoodFanSpeed.High)
    assert ok is True
    topics = [t for t, _ in fake_mqtt.published]
    request_topic = (
        f"cmd/{thing_mwo['thingTypeName']}/{thing_mwo['thingName']}/request/"
        f"{fake_mqtt.client_id}"
    )
    assert request_topic in topics
```

- [ ] **Step 2: Run**

Run: `pytest tests/awsiot/test_integration_microwave.py -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/awsiot/test_integration_microwave.py
git commit -m "test(awsiot): end-to-end integration test with FakeMqttClient"
```

---

## Task 18: Full suite gate — `pytest`, `ruff`, `basedpyright`, `pre-commit`

- [ ] **Step 1: Run the complete test suite**

Run: `pytest -v`
Expected: all tests PASS (both legacy HTTP and new AWS).

- [ ] **Step 2: Lint**

Run: `ruff check .`
Expected: PASS.

- [ ] **Step 3: Type check**

Run: `basedpyright`
Expected: PASS (0 errors).

- [ ] **Step 4: Pre-commit**

Run: `pre-commit run --all-files`
Expected: PASS or auto-fix and re-run.

- [ ] **Step 5: Fix any issues surfaced above**, recommitting as needed. Do not commit an empty "gate" commit if nothing changed.

---

## Task 19: `tools/capture_mwo_fixtures.py` — real-device fixture capture helper

A standalone async script that uses the new library to connect to the real microwave and write `thing_mwo.json`, `capability_mwo.json`, `state_mwo_full.json` to `tests/awsiot/data/` (overwriting placeholders). It deliberately does not depend on `kitchenaid_iot.py` — the point is to exercise the library's own code path.

**Files:**
- Create: `tools/__init__.py` (if absent)
- Create: `tools/capture_mwo_fixtures.py`

- [ ] **Step 1: Check whether `tools/__init__.py` already exists**

Run: `ls tools/__init__.py 2>/dev/null || echo MISSING`
Expected: either the path is printed or `MISSING` is printed.

- [ ] **Step 2: Create `tools/__init__.py`** if missing, as an empty file.

- [ ] **Step 3: Create `tools/capture_mwo_fixtures.py`**

```python
"""Capture fixture data for a KitchenAid microwave.

Usage:
    python -m tools.capture_mwo_fixtures \\
        --email you@example.com \\
        --password 'password' \\
        --brand KitchenAid \\
        --region US \\
        --said WPR1A00000001

Writes:
    tests/awsiot/data/thing_mwo.json
    tests/awsiot/data/capability_mwo.json
    tests/awsiot/data/state_mwo_full.json

The capability file is captured by reading the downloader's disk cache
after the first connect(), so this script also doubles as a smoke test
for the full discovery path.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

import aiohttp

from whirlpool.auth import Auth
from whirlpool.awsiot.appliancesmanager import AppliancesManager as AwsAppliancesManager
from whirlpool.backendselector import BackendSelector
from whirlpool.types import Brand, Region

LOGGER = logging.getLogger("capture_mwo_fixtures")

DATA_DIR = Path(__file__).resolve().parent.parent / "tests" / "awsiot" / "data"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument(
        "--brand", default="KitchenAid", choices=[b.name for b in Brand]
    )
    parser.add_argument("--region", default="US", choices=[r.name for r in Region])
    parser.add_argument(
        "--said",
        help="SAID of the microwave to capture (defaults to first discovered)",
    )
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


async def _amain(args: argparse.Namespace) -> int:
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    brand = Brand[args.brand]
    region = Region[args.region]
    backend = BackendSelector(brand, region)

    async with aiohttp.ClientSession() as session:
        auth = Auth(backend, args.email, args.password, session, store=True)
        await auth.do_auth()

        manager = AwsAppliancesManager(auth, session, lambda: None)
        ok = await manager.connect()
        if not ok:
            LOGGER.error("AWS IoT connect failed")
            return 1

        if not manager.microwaves:
            LOGGER.error("No microwave discovered")
            return 2

        mwo = manager.microwaves[0]
        if args.said and mwo.said != args.said:
            for m in manager.microwaves:
                if m.said == args.said:
                    mwo = m
                    break

        LOGGER.info("Capturing fixtures for %s (%s)", mwo.said, mwo.name)

        # Thing record: reconstruct what the manager saw.
        # (We only have ApplianceInfo here, so we write a reduced shape
        #  that satisfies the test fixtures.)
        thing_out = {
            "thingName": mwo.said,
            "thingTypeName": mwo.appliance_info.model_number,
            "attributes": {
                "Name": mwo.name.encode("utf-8").hex(),
                "Category": mwo.appliance_info.category.capitalize(),
                "Serial": mwo.appliance_info.serial_number,
                "CapabilityPartNumber": mwo.capability_profile.part_number,
            },
        }
        (DATA_DIR / "thing_mwo.json").write_text(
            json.dumps(thing_out, indent=2)
        )

        # Capability: dump the raw dict preserved on the profile.
        (DATA_DIR / "capability_mwo.json").write_text(
            json.dumps(mwo.capability_profile.raw, indent=2)
        )

        # State: dump the full accumulated state.
        (DATA_DIR / "state_mwo_full.json").write_text(
            json.dumps(mwo._state, indent=2)
        )

        LOGGER.info("Wrote fixtures to %s", DATA_DIR)

        await manager.disconnect()
    return 0


def main() -> None:
    args = _parse_args()
    sys.exit(asyncio.run(_amain(args)))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Verify the script at least imports cleanly**

Run: `python -m tools.capture_mwo_fixtures --help`
Expected: argparse usage printed, exit 0.

- [ ] **Step 5: Commit**

```bash
git add tools/__init__.py tools/capture_mwo_fixtures.py
git commit -m "tools: add MWO fixture capture helper"
```

---

## Task 20: Real-device fixture capture + swap placeholders

**This step requires the real KitchenAid microwave online and credentialed.** If the device is not available, skip to Task 21 and come back.

- [ ] **Step 1: Run the capture script against the real device**

Run:
```bash
python -m tools.capture_mwo_fixtures \
    --email YOUR_EMAIL \
    --password YOUR_PASSWORD \
    --brand KitchenAid \
    --region US \
    --verbose
```

Expected: three files overwritten in `tests/awsiot/data/`, exit code 0.

- [ ] **Step 2: Inspect the captured files**

Run: `jq . tests/awsiot/data/capability_mwo.json | head -60`
Expected: real Whirlpool capability file JSON.

Read: `tests/awsiot/data/state_mwo_full.json` and confirm paths used by `whirlpool/awsiot/microwave.py` (`primaryCavity.cavityState`, `primaryCavity.cavityLight`, `primaryCavity.cookTimer.time`, `hoodFan.userFanSpeed`, `hoodLight`, `hoodLightColor`, `remoteStartEnable`, `hmiControlLockout`, `quietMode`, `sabbathMode`) all exist or are correctable.

- [ ] **Step 3: Re-run unit tests against the real fixtures**

Run: `pytest tests/awsiot -v`
Expected: all tests PASS.

  - If `test_capabilities.py` fails because the real capability file has a different schema, update `parse_capability_profile` in `whirlpool/awsiot/capabilities.py` to handle the real shape. Keep the `CapabilityProfile` *dataclass* stable; only the parser changes.
  - If `test_microwave.py` getter assertions fail because a path is off, update the getters in `whirlpool/awsiot/microwave.py`. Do not update the tests' expected values unless the device genuinely reports a different vocabulary.
  - Update `capability_mwo_no_hood.json` by hand-editing a copy of the captured `capability_mwo.json` with hood addressees removed, so the feature-gating tests still run against a realistic shape.

- [ ] **Step 4: Commit captured fixtures + any parser/getter fixes**

```bash
git add tests/awsiot/data/thing_mwo.json tests/awsiot/data/capability_mwo.json tests/awsiot/data/state_mwo_full.json tests/awsiot/data/capability_mwo_no_hood.json
# Include any parser/getter fixes
git add -p whirlpool/awsiot/capabilities.py whirlpool/awsiot/microwave.py
git commit -m "test(awsiot): replace placeholder fixtures with real MWO captures"
```

---

## Task 21: Real-device validation checklist

Hand-drive the library against the microwave. The checklist mirrors the spec's "Real-device validation checklist". Use a short REPL script or an enhanced CLI menu — whatever is fastest.

- [ ] **Step 1: Launch an interactive session**

Write a throwaway script `scratch_mwo.py` (do NOT commit) that:
  1. Authenticates with `BackendSelector(Brand.KitchenAid, Region.US)` + `Auth`.
  2. Instantiates the top-level facade `AppliancesManager` and calls `connect()`.
  3. Grabs `manager.microwaves[0]` and drops into `asyncio.get_event_loop().run_until_complete(...)` calls or an `asyncio` REPL.

- [ ] **Step 2: Work through the validation items and record pass/fail in the PR body template:**

- [ ] Library discovers the microwave on `connect()`
- [ ] Initial state populates; all getters return plausible values
- [ ] Cavity light toggles on/off (`await mwo.set_cavity_light(True)` / `False`)
- [ ] Hood light cycles through all four levels
- [ ] Hood light color changes through all three colors
- [ ] Hood fan cycles through all five speeds
- [ ] Starting a 30-second microwave cook at 50% power works; state transitions idle → cooking → completed
- [ ] Cancel mid-cook works; state transitions cooking → idle
- [ ] Physical door open/close reflects in `get_door_status()`
- [ ] Unplugging the microwave flips `get_online()` to False within ~10s via presence topic
- [ ] Plugging back in flips it to True and auto-fetches fresh state

- [ ] **Step 3: Fix any issues found.** Each fix is its own focused commit with a descriptive message (e.g., `fix(awsiot): hood fan speed "med" round-trip`). Re-run `pytest -v` after each fix.

- [ ] **Step 4: Stash or delete the scratch script.** Do not commit it.

---

## Task 22: Push the fork and open the draft PR

- [ ] **Step 1: Verify branch state**

Run: `git status && git log --oneline origin/aws_iot..HEAD`
Expected: clean working tree; commit log mirrors the task sequence in this plan.

- [ ] **Step 2: Add the fork remote** (if not already)

```bash
git remote -v
# If no "fork" remote yet:
git remote add fork git@github.com:<your-user>/whirlpool-sixth-sense.git
```

- [ ] **Step 3: Push to the fork**

```bash
git push -u fork aws_iot-scaffolding
```

- [ ] **Step 4: Open the draft PR**

Use `gh pr create --draft` against `abmantis:aws_iot` (base) from `<your-user>:aws_iot-scaffolding` (head). Body template:

```markdown
## AWS IoT scaffolding + capability-driven appliance routing

Closes #117 (partial — Microwave support), Closes #122.

This PR fills in the `whirlpool/awsiot/` path that was scaffolded in the
initial `aws_iot` commit. It adds:

- Async-safe `MqttClient` (no handler runs on paho threads)
- Capability file download + parse + cache (#122)
- Capability-driven `ApplianceFactory` for class routing
- New top-level `Microwave` ABC
- Concrete `awsiot.Microwave` matching KitchenAid MWO feature set
- Stubs for Aircon/Dryer/Washer/Oven/Refrigerator (factory-registered)
- Test fixtures + unit coverage for the AWS path

Architecture mirrors the existing `httpapi/` layout. External API stays
stable across transports per #117 discussion.

### Design doc
See `docs/superpowers/specs/2026-04-11-aws-iot-scaffolding-design.md`.

### Real-device validation (pre-publish)
- [x] Library discovers the microwave on `connect()`
- [x] Initial state populates; all getters return plausible values
- [x] Cavity light toggles on/off
- [x] Hood light cycles through all four levels
- [x] Hood light color changes through all three colors
- [x] Hood fan cycles through all five speeds
- [x] Starting a 30-second microwave cook at 50% power works; idle→cooking→completed
- [x] Cancel mid-cook works; cooking→idle
- [x] Physical door open/close reflects in `get_door_status()`
- [x] Unplugging flips `get_online()` to False within ~10s
- [x] Plugging back in flips it to True and auto-fetches fresh state

cc @abmantis — would love your thoughts on the factory/matcher pattern
and whether the Microwave ABC shape looks right.
```

- [ ] **Step 5: Mark as draft**, confirm the URL, share it with the user for review.

---

## Self-review

- **Spec coverage**
  - Goal 1 (architectural completeness): Tasks 4–9, 12–15 cover MqttClient, capabilities, matchers, factory, Appliance base, stubs.
  - Goal 2 (unified API): Tasks 10, 11, 16 add the top-level `Microwave` ABC, HTTP stub, facade property.
  - Goal 3 (one working appliance): Task 13 implements the Microwave; Task 17 integration test; Task 21 real-device validation.
  - Goal 4 (capability-driven routing): Tasks 6, 7, 9, 15 build the capability download → factory pipeline.
  - Goal 5 (upstream-ready): Tasks 18, 20, 21, 22 cover test suite, lint, type check, real-device validation, draft PR.
  - Success criteria #2 (all getter/setter paths): covered in Task 13 test file.
  - Success criteria #4 (MQTT async-safe, TODO removed): Tasks 4, 5.
  - Success criteria #5 (tests cover all AWS pieces): every component has a paired test file.
  - Closes #117 (partial, microwave) and #122 (capability download): Tasks 6, 7, 13, 15.

- **Placeholder scan:** No `TBD`/`TODO` left in task bodies. Every code step has real code. Every command step has a real command.

- **Type consistency:** `CapabilityProfile`, `MqttClient`, `Appliance`, `Microwave` interfaces are defined in earlier tasks and referenced unchanged in later ones. `_send_command` signature (`addressee`, `command`, `**payload_extra`) is consistent across Task 12's appliance base and Task 13's concrete microwave. `Appliance.__init__` signature `(mqtt, appliance_info, capability_profile, initial_state_timeout=...)` is consistent across Tasks 12, 13, 14, 15. `DEFAULT_FACTORY.build` signature `(mqtt, profile, thing, appliance_info)` is consistent across Tasks 9 and 15.

- **Risks left for runtime:**
  - Capability file real schema may differ from placeholder shape; Task 20 explicitly includes a parser-update step.
  - AWS IoT state-update topic format is assumed from `kitchenaid_iot.py`; Task 21 catches any drift.
