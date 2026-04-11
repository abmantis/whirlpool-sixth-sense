# AWS IoT Scaffolding + Capability-Driven Appliance Routing

**Status:** Draft
**Date:** 2026-04-11
**Branch:** `aws_iot-scaffolding` (forked off `origin/aws_iot`)
**Closes:** #117 (partial — Microwave support), #122 (capability file download)

## Overview

Fill in the `whirlpool/awsiot/` path that was scaffolded in abmantis's initial AWS IoT commit on the `aws_iot` branch. Turn it into a complete, async-safe, contributor-friendly framework that can host any AWS-side appliance class, and prove the framework works by implementing a full `Microwave` subclass that controls a real KitchenAid microwave-over-range (MWO).

The architecture is the primary deliverable. The microwave is the end-to-end proof that the architecture is not just theoretical.

## Goals

1. **Architectural completeness.** Every structural piece that contributors need to add a new AWS-side appliance class is in place: async MQTT, capability file download + parsing, a factory for class routing, a thin base class with path-based state helpers, stub files per category, and a fixture-driven test harness.
2. **Unified public API.** The top-level `AppliancesManager` facade continues to present legacy (HTTP) and new (AWS IoT) appliances through identical consumer-facing interfaces. Home Assistant and other consumers never branch on transport. This matches abmantis's stated direction in the issue #117 discussion ("keep the external api stable and unified").
3. **One working appliance.** A `KitchenAid` microwave (over-range model with hood fan and hood light) is controllable end-to-end through the library with the same feature set as `tools/kitchenaid_iot.py` in the `kitchenaid_dev` reverse-engineering workspace.
4. **Capability-driven routing.** Classification of an AWS IoT thing into an appliance subclass is based on its parsed capability file, not on heuristics against `thingTypeName` or `Category`. This closes issue #122 and gives us a principled answer to the "microwave vs oven" problem raised in issue #117.
5. **Upstream-ready.** Code style, module layout, and commit discipline target a clean draft PR back to `abmantis/whirlpool-sixth-sense:aws_iot`.

## Non-goals

- Implementing Aircon, Dryer, Washer, Oven, or Refrigerator AWS-side subclasses beyond stubs. Those are contributor tasks unlocked by this scaffolding.
- EMEA region support for the AWS path. The `AWS_REGION = "us-east-2"` hardcode stays; routing this through `BackendSelector` is tracked as a follow-up.
- Changes to `whirlpool/httpapi/`. The legacy path is frozen for this work.
- A top-level `Microwave` HTTP implementation. Only an abstract `microwave.py` and a `NotImplementedError` stub in `httpapi/microwave.py` so the facade typechecks.
- Custom exception hierarchies beyond what already exists (`AuthException`) plus one new `CapabilityDownloadError` used internally in the downloader.
- Per-command requestId → response correlation. State updates are the authoritative confirmation path.
- Automatic command retries. Callers decide retry policy.

## Success criteria

1. A Home Assistant integration using this library can list a KitchenAid microwave alongside any existing HTTP-side appliances with no transport-specific code on the consumer side.
2. Start microwave, cancel, read cavity state, read/control cavity light, read/control hood light + color, read/control hood fan, and read all the mode flags (remote-start enable, HMI control lockout, quiet mode, Sabbath mode) all work end-to-end against the real device.
3. Capability file download (#122) is on the critical path for every AWS appliance and drives factory routing. No heuristics.
4. MQTT is fully async-safe: no handler coroutine runs on a paho network thread, `publish`/`subscribe`/`unsubscribe` are awaitable, and `MqttClient` carries no TODO comments about threading.
5. Tests cover the AWS path with a fake MQTT client — the capability downloader, the factory, the base appliance class, and the `Microwave` subclass each have unit tests, plus at least one integration-style test that walks `connect() → getState → state update → command → callback` through a fake MQTT transport.
6. `basedpyright` and `ruff check` pass on every new file, matching abmantis's existing quality gates.
7. The real-device validation checklist (see "Real-device validation checklist" below) passes before the draft PR is opened against abmantis's repo.

## Background

### Current state of the `aws_iot` branch

The branch refactors the library into two parallel transport backends:

- **`whirlpool/httpapi/`** — the legacy REST + websocket path. All previously-top-level appliance files were moved here unchanged.
- **`whirlpool/awsiot/`** — the new AWS IoT (MQTT) path. Scaffolded with working auth chain, SigV4 URL signing, AWS IoT Things REST discovery, and a paho-mqtt-based `MqttClient`. A base `awsiot.Appliance` class can send `getState` and receive state updates. No category-specific subclasses exist yet — `_add_appliance` in `awsiot/appliancesmanager.py` has empty `pass` branches for every category and always constructs a bare `Appliance` instance.

The top-level `whirlpool/appliancesmanager.py` is now a facade. It runs both managers in parallel on `connect()`, treats HTTP success as required and AWS success as optional, and concatenates results through per-category properties (`aircons`, `dryers`, etc.). Top-level device files like `whirlpool/oven.py` were converted to abstract base classes defining the public contract, and `httpapi/oven.py` provides the HTTP-backed implementation.

### What's missing

- AWS-side device subclasses for every category.
- No `Microwave` abstract class exists anywhere in the library — the microwave type is entirely absent from the public API.
- `awsiot/appliancesmanager.py` has an `asyncio.sleep(5)` TODO compensating for the fact that appliances don't actually wait for state.
- `awsiot/appliance.py::get_online()` raises `NotImplementedError`.
- `MqttClient` uses paho with threading and has a `TODO: the mqtt methods here should be made async-safe` comment at module level.
- Capability file handling (issue #122) is not implemented — there are commented-out lines in `awsiot/appliance.py` showing where it would go.
- No tests exist for the AWS path. The existing fixtures in `tests/` are all wired for the HTTP path.
- Category routing in `_add_appliance` can't distinguish a microwave from an oven because AWS IoT's `Category` attribute is the same for both (`cooking`).

### Reference implementation

`tools/kitchenaid_iot.py` in the `kitchenaid_dev` reverse-engineering workspace is a working CLI that controls a KitchenAid MWO through AWS IoT end-to-end. It uses `awscrt`/`aws-iot-device-sdk` rather than paho, defines its own SigV4 signing, and has no abstraction layer — it is a 923-line script, not a library. Its value for this design is the concrete device feature set and MQTT payload shapes, which are the ground truth for how commands and state are represented on the wire.

Feature set of the reference (all of which we target):

- **Cavity state:** `cavityState`, `doorStatus`, `doorLockStatus`, `recipeId`, `recipeExecutionState`, `mwoPowerLevel`, `cavityLight`, `turnTable`, `ovenDisplayTemperature`, `temperatureUnit`, `cookTimer { state, time, timeComplete }`.
- **Hood:** `hoodLight` (off / low / med / high), `hoodLightColor` (warmWhite / naturalWhite / coolWhite), `hoodFan { userFanSpeed }` (off / low / med / high / boost).
- **Modes:** `remoteStartEnable` (read-only, must be set on the physical panel), `hmiControlLockout`, `quietMode`, `sabbathMode`.
- **Commands:** MQTT addressee-based routing. Addressee values: `appliance` (for getState), `primaryCavity` (cavity commands), `hoodFan`, `hoodLight`. Command verbs: `getState`, `run`, `set`, `cancel`. Recipe IDs: `microwave`, `reheat`, `defrost`, `soften`.

### Key architectural decisions (from brainstorming)

| Decision | Choice | Rationale |
|---|---|---|
| Scope | Architecture-first + microwave as example | Full framework is too large; architecture-only leaves no validation of the design; microwave-as-example gives both |
| Destination | Upstream to abmantis | Draft PR against `abmantis:aws_iot`; strict convention matching; no private-fork divergence |
| MQTT library | paho-mqtt, refactored async-safe | Already in the branch; matches abmantis's dependency choice; avoids adding `awscrt` |
| Class routing | Capability file first, then factory | Closes #122 in the same work; only principled answer to MWO-vs-oven; no heuristic maintenance burden |
| ABC strategy | Keep existing ABCs, add Microwave at top level | Matches abmantis's pattern; unified API preserved; no new abstractions contributors need to learn |
| Microwave ABC scope | Core cavity + hood + modes; recipe as parameter | Avoids per-recipe method explosion; covers the real device's feature set |
| Delivery sequencing | Local iteration + real-device validation, **then** draft PR | User preference: polish before publicizing |

## Architecture

### Module layout

```
whirlpool/
├── appliance.py                # unchanged — abstract base (said, name, fetch_data, get_online, callbacks)
├── appliancesmanager.py        # updated — add `microwaves` property to facade
├── microwave.py                # NEW — abstract Microwave ABC, parallel to oven.py
├── oven.py                     # unchanged
├── dryer.py, washer.py, aircon.py, refrigerator.py   # unchanged
│
├── httpapi/
│   ├── microwave.py            # NEW — NotImplementedError stub; keeps facade typechecks clean
│   └── (everything else unchanged)
│
└── awsiot/
    ├── __init__.py             # unchanged
    ├── auth.py                 # unchanged (Cognito + SigV4 + credential caching)
    ├── signing.py              # unchanged (SigV4 URL + header construction)
    ├── things.py               # unchanged (AWS IoT Things REST)
    ├── mqttclient.py           # REWRITTEN — async-safe paho wrapper
    ├── capabilities.py         # NEW — CapabilityProfile + CapabilityDownloader
    ├── factory.py              # NEW — ApplianceFactory + @register_appliance decorator
    ├── matchers.py             # NEW — has_addressee / has_feature / has_command / model_prefix helpers
    ├── appliance.py            # REFACTORED — thin base, _get_path helpers, _send_command, presence handling
    ├── appliancesmanager.py    # REFACTORED — uses factory, drives capability download per thing
    ├── microwave.py            # NEW — concrete awsiot.Microwave
    ├── aircon.py               # NEW — factory-registered stub, NotImplementedError bodies
    ├── dryer.py                # NEW — same
    ├── washer.py               # NEW — same
    ├── oven.py                 # NEW — same
    └── refrigerator.py         # NEW — same

tests/
└── awsiot/                     # NEW test directory for the AWS path
    ├── __init__.py
    ├── conftest.py             # FakeMqttClient fixture + capability/thing/state fixtures
    ├── data/
    │   ├── capability_mwo.json
    │   ├── thing_describe_mwo.json
    │   ├── state_mwo_full.json
    │   └── state_mwo_cooking.json
    ├── test_capabilities.py
    ├── test_factory.py
    ├── test_matchers.py
    ├── test_mqttclient.py
    ├── test_appliancesmanager.py
    ├── test_appliance_base.py
    ├── test_microwave.py
    └── test_integration_microwave.py
```

### Class hierarchy

```
                 Appliance (whirlpool/appliance.py)                 ← unchanged
                 /                                          \
       httpapi.Appliance                              awsiot.Appliance
       (existing)                                     (refactored — thin base)
              │                                             │
              │                                             │
     (existing httpapi subclasses)             ┌────────────┼────────────┬──────────────┬──────────┐
                                               │            │            │              │          │
                                       awsiot.Microwave  awsiot.Oven   awsiot.Dryer  awsiot.Washer  …stubs
                                               │
                                       implements Microwave ABC (whirlpool/microwave.py)


                 Microwave (whirlpool/microwave.py)          ← NEW top-level ABC
                      │
                      ├─ implemented by awsiot.Microwave    (full implementation)
                      └─ httpapi.Microwave                  (stub, NotImplementedError)
```

### Design commitments this layout makes

1. **One responsibility per file.** `mqttclient.py` only does MQTT transport. `capabilities.py` only does capability files. `factory.py` only does class routing. `appliance.py` (awsiot) only does state/command plumbing. Device classes only do domain logic.
2. **Contributors have a single template to follow.** Stub files for every category, each ~15 lines, each already registered with the factory. Adding a real appliance type is filling in one file, capturing a capability fixture, and adding one test file.
3. **Parallelism with `httpapi/`.** The `awsiot/` subtree mirrors the shape of `httpapi/` (manager, appliance, one file per device type). Anyone who reads `httpapi/` can navigate `awsiot/`.
4. **New ABCs land at the top level.** `Microwave` is defined at `whirlpool/microwave.py` even though only AWS implements it — because abmantis's convention is that `whirlpool/<device>.py` is the public contract and transport subdirs hold implementations.
5. **The facade routes by ABC, not by transport class.** `AwsAppliancesManager._register` uses `isinstance(appliance, MicrowaveABC)` (the top-level ABC) rather than `isinstance(appliance, awsiot.Microwave)`. This means any future AWS subclass that inherits a top-level ABC lands in the right category bucket automatically.

## Components

### `awsiot/mqttclient.py` — async-safe MQTT transport

**Interface:**

```python
class MqttClient:
    def __init__(self, aws_auth: Auth) -> None: ...

    async def connect(self) -> bool: ...
    async def disconnect(self) -> None: ...
    def is_connected(self) -> bool: ...

    @property
    def client_id(self) -> str | None: ...

    async def subscribe(self, topic: str) -> None: ...
    async def unsubscribe(self, topic: str) -> None: ...
    async def publish(self, topic: str, payload: dict[str, Any]) -> None: ...

    def add_message_handler(
        self, handler: Callable[[str, dict[str, Any]], Awaitable[None]]
    ) -> None: ...
    def remove_message_handler(self, handler) -> None: ...

    def add_connection_handler(
        self,
        on_connect: Callable[[], Awaitable[None]] | None = None,
        on_disconnect: Callable[[], Awaitable[None]] | None = None,
    ) -> None: ...
```

**Key refactors vs the current `aws_iot` branch:**

1. **Async boundary is explicit.** `subscribe`, `unsubscribe`, `publish` are all coroutines. Internally they wrap paho's synchronous calls in `loop.run_in_executor(None, ...)` so the event loop never blocks on a paho call.
2. **Incoming messages go through an `asyncio.Queue`, not a direct callback.** Paho's `_on_message` (runs on paho's network thread) only does `loop.call_soon_threadsafe(queue.put_nowait, (topic, payload))`. A dedicated `_dispatch_loop()` coroutine reads from the queue and awaits each registered handler. **No handler ever runs on a paho thread.** This is the single biggest correctness fix from the current branch.
3. **Handler list instead of single callback.** The current branch has one `message_callback`. We replace that with `add_message_handler`/`remove_message_handler` so `AppliancesManager`, the capability downloader, and individual appliances can all attach independently.
4. **Connection lifecycle handlers.** `add_connection_handler(on_connect, on_disconnect)` gives consumers a hook for reconnection. Appliances use this to re-request state after a reconnect.
5. **Idempotent subscriptions.** Tracks subscribed topics in a set; already-subscribed is a no-op. On reconnect, re-subscribes everything in the set automatically.
6. **Exception isolation in the dispatch loop.** If a registered handler raises, the dispatch loop logs at ERROR and continues. One bad handler does not kill message delivery for the rest.

**What we keep:** `signing.py` SigV4 URL construction, the WebSocket path assembly, the TLS setup, the `wt.applianceconnect.net` endpoint. We are refactoring the threading/async boundary, not rewriting the paho integration.

**Testability:** The entire class talks to paho via a small number of methods. A `FakeMqttClient` in `tests/awsiot/conftest.py` implements the same public interface backed by in-memory state — almost every awsiot test uses the fake, and `test_mqttclient.py` is the only file that touches real paho (with `paho.mqtt.client.Client` mocked).

### `awsiot/capabilities.py` — capability download, parse, cache

Implements issue #122 and becomes the basis for class routing.

**Interface:**

```python
@dataclass(frozen=True)
class CapabilityProfile:
    """Parsed capability file for a single appliance model."""
    part_number: str
    raw: dict[str, Any]                       # full parsed JSON
    features: frozenset[str]                  # normalized feature identifiers
    addressees: frozenset[str]                # primaryCavity, hoodFan, hoodLight, ...
    commands: dict[str, frozenset[str]]       # addressee -> allowed commands
    metadata: dict[str, Any]                  # appliance type hints, model family, etc.

    def has_feature(self, feature: str) -> bool: ...
    def has_addressee(self, addressee: str) -> bool: ...
    def supports_command(self, addressee: str, command: str) -> bool: ...


class CapabilityDownloadError(Exception):
    """Raised when a capability file cannot be retrieved or parsed."""


class CapabilityDownloader:
    def __init__(
        self,
        mqtt: MqttClient,
        session: aiohttp.ClientSession,
        cache_dir: Path | None = None,
    ) -> None: ...

    async def get(
        self,
        said: str,
        model_number: str,
        capability_part_number: str,
    ) -> CapabilityProfile:
        """Download, parse, and cache. Returns cached profile on subsequent calls."""
```

**Flow inside `get()`:**

1. Check in-memory cache keyed by `capability_part_number`. Hit → return.
2. Check on-disk cache (if `cache_dir` is set) at `<cache_dir>/<capability_part_number>.json`. Hit → parse, populate in-memory cache, return.
3. Subscribe the downloader's response handler to `api/capability/download/{model}/{said}/response`.
4. Publish a request to `api/capability/download/{model}/{said}` with `{"capabilityPartNumber": capability_part_number}`.
5. Await a future that resolves when the response handler fires, bounded by `asyncio.wait_for` with a ~10s timeout. The response carries a URL to the actual capability JSON file.
6. `aiohttp.GET` the capability file URL, parse the JSON body, run it through `_parse_capability_profile()` to produce a `CapabilityProfile`.
7. Write to disk cache if enabled. Populate in-memory cache. Unsubscribe from the response topic. Return the profile.

**Parser:** `_parse_capability_profile(raw: dict) -> CapabilityProfile` extracts normalized fields. Unknown fields go into `.raw` and `.metadata` so subclasses can reach into transport-specific details when needed, but the top-level `features` / `addressees` / `commands` give the factory and most appliance code a stable, normalized view.

**Caching.** Capability files are model-level, not device-level — two identical KitchenAid microwaves share a `capabilityPartNumber` and therefore a profile. The in-memory cache deduplicates within a session; the optional disk cache deduplicates across restarts. Abmantis's existing dot-file pattern (`.whirlpool_auth.json`) is the precedent — we use `.whirlpool_capabilities/` as the default when `cache_dir` is not explicitly set, controlled by the same `store=True` flag the auth module uses.

**Why capability download goes through MQTT, not HTTPS:** the Whirlpool cloud exposes capability files only via the MQTT request/response topic pair. No REST equivalent exists.

**Open question for implementation:** The exact structure of the capability file is unknown until we capture one from the real device. The `CapabilityProfile` *interface* above is stable; the *parser internals* are provisional and will be finalized against a captured fixture as the first implementation task.

### `awsiot/factory.py` — appliance class registry & routing

**Interface:**

```python
Matcher = Callable[[CapabilityProfile, dict[str, Any]], bool]


@dataclass
class Registration:
    matcher: Matcher
    cls: type["awsiot.Appliance"]
    priority: int  # higher wins when multiple matchers fire


class ApplianceFactory:
    def __init__(self) -> None: ...

    def register(
        self,
        cls: type["awsiot.Appliance"],
        matcher: Matcher,
        priority: int = 0,
    ) -> None: ...

    def build(
        self,
        mqtt: MqttClient,
        profile: CapabilityProfile,
        thing: dict[str, Any],
        appliance_info: ApplianceInfo,
    ) -> "awsiot.Appliance | None":
        """Return an instance of the highest-priority matching class, or None."""


DEFAULT_FACTORY = ApplianceFactory()


def register_appliance(
    matcher: Matcher,
    priority: int = 0,
) -> Callable[[type], type]:
    """Decorator: a subclass self-registers with DEFAULT_FACTORY at import time."""
```

**Usage in a subclass:**

```python
# whirlpool/awsiot/microwave.py

from .factory import register_appliance
from .matchers import has_addressee, has_feature

@register_appliance(
    matcher=lambda p, t: (
        has_addressee("primaryCavity")(p, t)
        and has_feature("microwaveOven")(p, t)
    ),
    priority=10,  # higher than generic Oven so MWO wins when both could match
)
class Microwave(Appliance, MicrowaveABC):
    ...
```

**Why priority matters.** Both ovens and microwaves have `primaryCavity`. Only microwaves have the `microwaveOven` feature. The matcher distinguishes them, and the priority knob resolves edge cases deterministically without introducing a separate "most specific wins" heuristic.

**Priority tie-break.** If two registrations match with equal priority, first-registered wins and a WARNING is logged. This is deterministic and makes conflicts visible.

**How the manager invokes it:**

```python
profile = await self._capability_downloader.get(said, model, cap_part_number)
appliance = DEFAULT_FACTORY.build(self._mqtt, profile, thing, appliance_info)
if appliance is None:
    LOGGER.warning(
        "No AWS appliance class matches %s (features=%s, addressees=%s)",
        said, sorted(profile.features), sorted(profile.addressees),
    )
    return
await appliance.connect()
self._register(appliance)
```

**Stubs register too.** `awsiot/oven.py`, `awsiot/dryer.py`, etc. each have a `@register_appliance` decorator with a matcher and a class body whose methods raise `NotImplementedError`. They surface in the factory but log when invoked, giving contributors a clear starting point: pick a stub, fill in its methods, capture a capability fixture, add a test.

**Why the factory is its own module:** decouples registration from `appliancesmanager.py`. Contributors adding a new appliance type touch exactly one file in `awsiot/` and the decorator wires it up.

### `awsiot/matchers.py` — matcher helpers

Small companion to `factory.py`. Named closures for the common matching patterns, giving subclass authors a readable DSL and tests a canonical way to assert "this matcher matches this profile."

```python
def has_addressee(name: str) -> Matcher: ...
def has_feature(name: str) -> Matcher: ...
def has_command(addressee: str, command: str) -> Matcher: ...
def model_prefix(prefix: str) -> Matcher: ...
def thing_category(name: str) -> Matcher: ...

def all_of(*matchers: Matcher) -> Matcher: ...
def any_of(*matchers: Matcher) -> Matcher: ...
def not_(matcher: Matcher) -> Matcher: ...
```

Each matcher is a tiny closure returning `(CapabilityProfile, dict) -> bool`. Tests in `test_matchers.py` cover one positive and one negative case each.

### `awsiot/appliance.py` — thin base class

**Interface:**

```python
class Appliance(BaseAppliance):
    def __init__(
        self,
        mqtt: MqttClient,
        appliance_info: ApplianceInfo,
        capability_profile: CapabilityProfile,
    ) -> None: ...

    @property
    def capability_profile(self) -> CapabilityProfile: ...

    async def connect(self) -> None:
        """Subscribe topics, register handlers, request initial state."""

    async def disconnect(self) -> None:
        """Unsubscribe topics, remove handlers."""

    @override
    async def fetch_data(self) -> bool:
        """Re-request full state (getState); returns True on state arrival, False on timeout."""

    @override
    def get_online(self) -> bool | None: ...

    # --- protected helpers for subclasses ---
    def _get_path(self, path: str) -> Any | None: ...
    def _get_path_int(self, path: str) -> int | None: ...
    def _get_path_bool(self, path: str) -> bool | None: ...
    def _get_path_str(self, path: str) -> str | None: ...
    def _get_path_float(self, path: str) -> float | None: ...

    async def _send_command(
        self,
        addressee: str,
        command: str,
        **payload_extra: Any,
    ) -> None: ...
```

**Behavior:**

1. **On `connect()`:** subscribe to the four per-appliance topics (`cmd/.../response/{client_id}`, `dt/.../state/update`, `$aws/events/presence/connected/{said}`, `$aws/events/presence/disconnected/{said}`), register itself as an MQTT handler filtered to those topics, register a `MqttClient.on_connect` handler that re-runs `fetch_data()` after reconnect, then `await self.fetch_data()` to populate initial state.
2. **State tracking:** `self._state: dict` is the merged JSON tree. Responses to `getState` replace it wholesale. `dt/.../state/update` messages are **deep-merged** into it (critical for partial state updates — deltas must not wipe sibling keys).
3. **Online tracking:** presence topics set `self._online` to `True` or `False`. `get_online()` returns that value; no `NotImplementedError`.
4. **Callback fanout:** after any state change, iterate `self._attr_changed` callbacks (inherited from `BaseAppliance`) exactly the way the HTTP side does. Exceptions in a callback are caught, logged at ERROR, and do not prevent other callbacks from firing.
5. **`_send_command` builds the full MQTT payload** with `requestId` (uuid4), `timestamp` (epoch millis), and `payload { addressee, command, **payload_extra }` wrapper. Publishes to `cmd/{model}/{said}/request/{client_id}`. Subclasses do not construct payloads directly.
6. **Path helpers** (`_get_path`, `_get_path_bool`, `_get_path_int`, `_get_path_str`, `_get_path_float`): dot-notation read-only access into `self._state`. `self._get_path_bool("primaryCavity.cavityLight")` is equivalent to `self._state.get("primaryCavity", {}).get("cavityLight")` coerced to bool, with None for missing paths or wrong types.

**`fetch_data()` semantics:** publishes `getState` with `addressee = "appliance"`, awaits an `asyncio.Event` set when the response arrives, bounded by a 5s timeout. Returns `True` on success, `False` on timeout. This gives Home Assistant a real signal instead of fire-and-forget.

**`deep_merge(base: dict, update: dict) -> dict`** is a module-private helper (same semantics as `kitchenaid_iot.py::deep_merge`). Unit-tested against edge cases: nested dicts, list-where-dict expected (log warning, keep existing), None values, empty dicts.

**Concurrency:** `self._state` is only read or written on the event loop thread. The dispatch loop in `MqttClient` is the only path that writes state on incoming messages, and it runs as a coroutine. No lock needed.

### `whirlpool/microwave.py` — top-level `Microwave` ABC

New public contract. Parallel to `whirlpool/oven.py`. No transport dependency.

```python
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
    def get_display_temperature_unit(self) -> str | None: ...  # "F" or "C"
    @abstractmethod
    def get_turntable_enabled(self) -> bool | None: ...

    # --- cook / timer ---
    @abstractmethod
    def get_active_recipe_id(self) -> str | None: ...
    @abstractmethod
    def get_recipe_execution_state(self) -> str | None: ...
    @abstractmethod
    def get_mwo_power_level(self) -> int | None: ...  # 0-100
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
        power_level: int,       # 1-100
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

**ABC design notes:**

- **Enums wherever the vocabulary is finite.** Matches abmantis's existing style in `oven.py` (`CookMode`, `CavityState`, `CookOperation`).
- **Getters return `T | None`** because a feature may not exist on every model. Over-the-range MWOs have hood features; counter-top MWOs do not. Consumers check for `None` — same pattern as the HTTP-side appliances.
- **Setters return `bool`** (success/failure), matching the existing convention. The docstring on each setter must explicitly state that `True` means "command published successfully to MQTT at QoS1"; the authoritative confirmation comes via the subsequent state update.
- **`start_cook(recipe, power_level, duration_seconds)` is a single method.** Recipe is a parameter, not a separate method per recipe. Keeps the ABC lean.
- **Hood controls are in the ABC** even though they are unusual. Models without a hood return `None` from `get_hood_*`, return `False` from `set_hood_*` with a WARNING log line, and do not publish anything on the wire.
- **No `feature_supported(name)` predicate on the ABC.** Consumers that need to know walk `appliance.capability_profile.has_addressee("hoodFan")`. We do not pollute the ABC with a gating method that duplicates the profile's interface.

### `awsiot/microwave.py` — concrete implementation

Translation layer between the MQTT state JSON and the `Microwave` ABC. Thin — every method is 2-6 lines.

```python
from typing import override

from ..microwave import (
    Microwave as MicrowaveABC,
    MicrowaveCavityState,
    MicrowaveDoorStatus,
    RecipeId,
    HoodFanSpeed,
    HoodLightLevel,
    HoodLightColor,
)
from .appliance import Appliance
from .factory import register_appliance
from .matchers import all_of, has_addressee, has_feature

LOGGER = logging.getLogger(__name__)

_CAVITY_STATE_MAP = {
    "idle": MicrowaveCavityState.Idle,
    "cooking": MicrowaveCavityState.Cooking,
    "paused": MicrowaveCavityState.Paused,
    "completed": MicrowaveCavityState.Completed,
}

_HOOD_FAN_MAP = {e.value: e for e in HoodFanSpeed}
_HOOD_LIGHT_MAP = {e.value: e for e in HoodLightLevel}
_HOOD_LIGHT_COLOR_MAP = {e.value: e for e in HoodLightColor}


@register_appliance(
    matcher=all_of(
        has_addressee("primaryCavity"),
        has_feature("microwaveOven"),
    ),
    priority=10,
)
class Microwave(Appliance, MicrowaveABC):
    # --- cavity ---
    @override
    def get_cavity_state(self) -> MicrowaveCavityState:
        raw = self._get_path_str("primaryCavity.cavityState")
        return _CAVITY_STATE_MAP.get(raw, MicrowaveCavityState.Unknown)

    @override
    def get_cavity_light(self) -> bool | None:
        return self._get_path_bool("primaryCavity.cavityLight")

    @override
    async def set_cavity_light(self, on: bool) -> bool:
        await self._send_command("primaryCavity", "set", cavityLight=on)
        return True

    # --- cook ---
    @override
    async def start_cook(
        self,
        recipe: RecipeId,
        power_level: int,
        duration_seconds: int,
    ) -> bool:
        if not 1 <= power_level <= 100:
            raise ValueError("power_level must be 1..100")
        if duration_seconds < 1:
            raise ValueError("duration_seconds must be >= 1")
        if not self.get_remote_start_enabled():
            LOGGER.warning("Remote start not enabled on %s", self.said)
            return False
        await self._send_command(
            "primaryCavity", "run",
            recipeID=recipe.value,
            mwoPowerLevel=float(power_level),
            cookTimer={"command": "start", "time": duration_seconds},
        )
        return True

    @override
    async def cancel_cook(self) -> bool:
        await self._send_command("primaryCavity", "cancel")
        return True

    # --- hood ---
    @override
    def get_hood_fan_speed(self) -> HoodFanSpeed | None:
        raw = self._get_path_str("hoodFan.userFanSpeed")
        return _HOOD_FAN_MAP.get(raw) if raw else None

    @override
    async def set_hood_fan_speed(self, speed: HoodFanSpeed) -> bool:
        if not self.capability_profile.has_addressee("hoodFan"):
            LOGGER.warning("Model %s has no hood fan", self.said)
            return False
        await self._send_command("hoodFan", "set", value=speed.value)
        return True

    # ... (remaining getters and setters follow the same pattern)
```

**The entire class is a translation layer.** No state management, no MQTT handling, no lifecycle. Those live in `Appliance`. That's the template for future appliance classes.

**Remote-start gate on `start_cook`** is user-safety. The physical appliance won't honor the command if remote start isn't enabled, so failing fast with a log line is better than silently publishing a no-op.

**Feature-absence on hood setters:** `self.capability_profile.has_addressee("hoodFan")` check before publishing. Returns False with a WARNING. Avoids publishing commands a model cannot execute.

### `awsiot/appliancesmanager.py` — refactored orchestrator

Ties components together. Most interesting logic is in helpers above.

```python
async def connect(self) -> bool:
    try:
        if not await self._mqtt.connect():
            LOGGER.error("Failed to connect to MQTT")
            return False

        things = await Things(self._aws_auth, self._session).list_things()
        if not things:
            LOGGER.info("No AWS IoT things for this account")
            return True  # not a failure — account may simply have no TS devices

        for thing in things:
            try:
                await self._add_appliance(thing)
            except Exception:
                LOGGER.exception(
                    "Failed to add appliance %s",
                    thing.get("thingName"),
                )
                continue  # per-appliance error isolation

    except AuthException as e:
        LOGGER.error("AWS auth failed: %s", e)
        return False

    return True


async def _add_appliance(self, thing: dict[str, Any]) -> None:
    info = self._build_info(thing)
    cap_part_number = thing["attributes"].get("CapabilityPartNumber")
    if not cap_part_number:
        LOGGER.warning(
            "Thing %s has no CapabilityPartNumber; cannot route", info.said,
        )
        return

    profile = await self._capability_downloader.get(
        info.said, info.model_number, cap_part_number,
    )

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
    """Route to the right category dict by top-level ABC, not transport class."""
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
    self.__dict__.pop("all_appliances", None)  # invalidate cached_property
```

**Properties:**

- **Per-appliance error isolation.** One device failing capability download or class routing doesn't abort the loop.
- **The manager does not know about transport-specific classes.** `isinstance` checks against top-level ABCs.
- **The `asyncio.sleep(5)` TODO is gone.** `appliance.connect()` awaits initial state directly.
- **`microwaves` property** added on both this manager and on the top-level `AppliancesManager` facade, mirroring existing per-category properties.

### `whirlpool/appliancesmanager.py` — facade update

One small addition to the facade — a `microwaves` property concatenating `http.microwaves + aws.microwaves`. The HTTP manager exposes an empty `_microwaves: dict` so its `microwaves` property returns `[]`. This keeps the facade's pattern uniform across all categories.

### `whirlpool/httpapi/microwave.py` — stub

```python
from ..microwave import Microwave as MicrowaveABC


class Microwave(MicrowaveABC):
    """Placeholder. Legacy REST API does not support microwaves.

    All methods raise NotImplementedError. This exists only so the top-level
    facade can typecheck against a concrete Microwave class on the HTTP side.
    """
    # Abstract methods raise NotImplementedError via ABC inheritance.
```

No factory registration, no constructor override. It is never instantiated. Present purely for type consistency.

### Category stubs in `awsiot/`

`awsiot/aircon.py`, `awsiot/dryer.py`, `awsiot/washer.py`, `awsiot/oven.py`, `awsiot/refrigerator.py` each register with the factory using a simple `has_addressee` or `thing_category` matcher, inherit from both `Appliance` and the corresponding top-level ABC, and have method bodies that raise `NotImplementedError` with a message pointing at the ABC method name.

Example (`awsiot/oven.py`):

```python
from ..oven import Oven as OvenABC
from .appliance import Appliance
from .factory import register_appliance
from .matchers import all_of, has_addressee, not_, has_feature


@register_appliance(
    matcher=all_of(
        has_addressee("primaryCavity"),
        not_(has_feature("microwaveOven")),
    ),
    priority=5,  # lower than Microwave's 10
)
class Oven(Appliance, OvenABC):
    """Stub. Contributors: fill in the OvenABC methods and add a test file."""
    # Abstract methods raise NotImplementedError via ABC inheritance.
```

This is the contributor template.

## Data flow

### Startup / discovery (happy path)

```
AppliancesManager.connect()
  │
  ├─► HttpAppliancesManager.connect()                [unchanged — ground truth]
  │     ├─ auth.do_auth()
  │     ├─ GET /api/v3/appliance/all/account/{acct}
  │     │     → legacyAppliance[] + tsAppliance[]
  │     ├─ _add_appliance() per entry
  │     │     • legacy → DATA_MODEL_KEY match → instantiated
  │     │     • ts     → falls through; logged at DEBUG "handled by AWS manager"
  │     ├─ GET /api/v1/appliance/shared (optional)
  │     ├─ fetch_data() per instantiated appliance
  │     └─ start EventSocket
  │
  └─► AwsAppliancesManager.connect()                 [refactored path]
        ├─ MqttClient.connect()
        │     ├─ Auth.create_signed_url(MQTT_ENDPOINT)
        │     │     ├─ get_cognito_identity_id()     [cached]
        │     │     └─ get_aws_credentials()         [cached, expiry-checked]
        │     ├─ paho.Client(transport="websockets")
        │     ├─ client.connect() via run_in_executor
        │     ├─ wait for _connected event (timeout 10s)
        │     └─ start _dispatch_loop() coroutine
        │
        ├─ Things.list_things()                      [AWS IoT REST, paginated]
        │     → list[ { thingName, thingTypeName, attributes{…} } ]
        │
        └─ for each thing:
              ├─ _build_info(thing) → ApplianceInfo
              │     said         = thing.thingName
              │     name         = hex-decoded attributes.Name
              │     category     = attributes.Category.lower()
              │     model_number = thing.thingTypeName
              │     serial       = attributes.Serial
              │
              ├─ CapabilityDownloader.get(said, model, capPartNumber)
              │     ├─ in-memory cache hit → return
              │     ├─ disk cache hit → parse + return
              │     ├─ mqtt.subscribe(".../response")
              │     ├─ mqtt.publish(request, {capabilityPartNumber})
              │     ├─ await future (timeout 10s)
              │     ├─ aiohttp GET the capability file URL
              │     ├─ _parse_capability_profile(raw)
              │     ├─ disk + memory cache write
              │     ├─ mqtt.unsubscribe(".../response")
              │     └─ return CapabilityProfile
              │
              ├─ DEFAULT_FACTORY.build(mqtt, profile, thing, info)
              │     ├─ iterate registrations sorted by priority desc
              │     ├─ first matcher returning True wins
              │     └─ instantiate cls(mqtt, info, profile)   or return None
              │
              ├─ if None: LOG warning; continue
              │
              ├─ appliance.connect()                 [awsiot.Appliance]
              │     ├─ mqtt.subscribe(cmd/.../response/{client_id})
              │     ├─ mqtt.subscribe(dt/.../state/update)
              │     ├─ mqtt.subscribe($aws/events/presence/connected/{said})
              │     ├─ mqtt.subscribe($aws/events/presence/disconnected/{said})
              │     ├─ mqtt.add_message_handler(self._handle_mqtt_message)
              │     ├─ mqtt.add_connection_handler(on_connect=self._on_reconnect)
              │     └─ await self.fetch_data()
              │           ├─ mqtt.publish(cmd/.../request/{client_id},
              │           │                {command: "getState", addressee: "appliance"})
              │           ├─ await self._initial_state_event  (timeout 5s)
              │           └─ return True/False
              │
              └─ self._register(appliance)           [isinstance-based category routing]
```

**Invariant:** HTTP connect must succeed; AWS connect can soft-fail with a warning. Matches current branch behavior.

### State update (device → library → consumer)

```
Device publishes   dt/{model}/{said}/state/update   { primaryCavity: { cavityLight: true } }
                          │
                          ▼
paho network thread  →  _on_message()
                          │  (paho thread — no asyncio state touched here)
                          │
                          └─► loop.call_soon_threadsafe(queue.put_nowait, (topic, payload))
                                              │
                                              ▼
asyncio event loop  →  MqttClient._dispatch_loop() (await queue.get())
                          │
                          └─► for handler in self._handlers:
                                 try: await handler(topic, payload)
                                 except: LOGGER.exception(); continue
                                              │
                                              ▼
                    Appliance._handle_mqtt_message(topic, payload)
                          │
                          ├─ dt/.../state/update          → deep_merge(self._state, payload)
                          ├─ cmd/.../response/{client_id} → deep_merge(self._state, payload["payload"])
                          │                                  and set _initial_state_event if waiting
                          ├─ /presence/connected/         → self._online = True
                          ├─ /presence/disconnected/      → self._online = False
                          │
                          └─► for cb in self._attr_changed: try: cb() except: log
                                              │
                                              ▼
                                 consumer callback fires (HA entity update)
```

**Why deep-merge and not replace:** state-update messages carry deltas. Replacing would wipe hood state every time a cavity field changes. This is the single trickiest correctness requirement — `kitchenaid_iot.py` learned it the hard way — and it's why `awsiot/appliance.py` gets a proper `deep_merge` helper with unit tests.

**Concurrency:** `self._state` is read and written on the event loop thread only. The paho network thread never touches Python-level appliance state.

### Command (consumer → library → device)

```
microwave.start_cook(RecipeId.Microwave, 80, 30)
                          │
                          ▼
Microwave.start_cook()
  ├─ validate (power 1..100, duration ≥ 1, remote_start_enabled)
  ├─ await self._send_command("primaryCavity", "run",
  │         recipeID="microwave",
  │         mwoPowerLevel=80.0,
  │         cookTimer={"command": "start", "time": 30})
  │         │
  │         ▼
  │   Appliance._send_command()
  │     ├─ build payload { requestId, timestamp, payload{addressee, command, ...} }
  │     └─ await self._mqtt.publish(cmd/.../request/{client_id}, payload)
  │         │
  │         ▼
  │       MqttClient.publish()
  │         └─ await loop.run_in_executor(None, self._client.publish, topic, json)
  │
  └─ return True   (published at QoS1)

[later, asynchronously]

Device publishes   cmd/{model}/{said}/response/{client_id}      (ack + partial state)
Device publishes   dt/{model}/{said}/state/update  { primaryCavity: { cavityState: "cooking" } }
                          │
                          ▼
                  (state update flow above — deep-merged, callback fanout)
```

**No application-level ack wait.** The state-update path is authoritative. HA's pattern is to optimistically mark an entity "pending" and let state updates confirm — this matches that pattern.

**We do NOT correlate `requestId` with response.** Not every command receives a response message; the state topic is the source of truth. Can be added later if a consumer needs it.

### Reconnect

```
paho _on_disconnect (unexpected)
     │
     ▼
loop.call_soon_threadsafe(self._connected.clear)
     │
     ▼
MqttClient._reconnect_loop()
     ├─ backoff: 1s, 2s, 4s, 8s, 16s, 30s (cap at 30s)
     ├─ re-sign URL  (credentials may have expired)
     ├─ paho.Client.reconnect() via executor
     ├─ on success: re-subscribe everything in self._subscribed_topics
     └─ fire on_connect handlers → appliances re-request initial state
```

**Credential expiry is the primary reconnect cause.** AWS Cognito credentials default to 1h. `Auth.get_aws_credentials()` is updated to check `now < expiration - 60s` before returning a cached value; otherwise it re-fetches.

**Appliances self-heal after reconnect** via the `on_connect` handler registered in `Appliance.connect()` which calls `self.fetch_data()`. State deltas missed during disconnect are gone forever; a fresh `getState` replaces `self._state` wholesale.

### Shutdown

```
AppliancesManager.disconnect()
  ├─ aws.disconnect()
  │     ├─ for each appliance: mqtt.unsubscribe(all its topics)
  │     ├─ mqtt.remove_message_handler(appliance._handle_mqtt_message)
  │     ├─ mqtt._dispatch_loop.cancel()
  │     ├─ mqtt._client.disconnect() via executor
  │     └─ mqtt._client.loop_stop() via executor
  │
  └─ http.disconnect()
        └─ stop EventSocket
```

Idempotent; safe to call multiple times. `MqttClient.disconnect()` is a no-op if already disconnected.

## Error handling

One rule: **never let one bad appliance kill discovery, and never let an exception escape a paho callback onto the event loop.**

| Failure | Behavior | Rationale |
|---|---|---|
| OAuth fails | `HttpAppliancesManager.connect()` returns False; top-level returns False | HTTP is ground truth |
| Cognito identity fetch fails | `AwsAppliancesManager.connect()` returns False; top-level logs WARNING, still returns True | AWS path is optional per abmantis's design |
| `list_things()` returns empty | Log INFO; `connect()` returns True | Valid state for accounts with no TS devices |
| `list_things()` raises | Log ERROR; `connect()` returns False | Distinct from empty; we do not know what we missed |
| MQTT connect fails / times out | Log ERROR; `AwsAppliancesManager.connect()` returns False | Cannot proceed without MQTT |
| Capability download times out | Log WARNING with said + part_number; skip appliance; continue loop | Per-appliance isolation |
| Capability parse fails | Log WARNING with said + raw preview; skip appliance; continue loop | Per-appliance isolation |
| No matcher fires | Log WARNING listing features + addressees; skip appliance; continue loop | Contributor signal |
| `appliance.connect()` raises | `try/except` in `_add_appliance` loop; `LOGGER.exception`; continue | Per-appliance isolation |
| `fetch_data()` times out on initial state | Return False; appliance still registered; WARNING logged | Device may be offline; state will arrive later |
| Command publish fails (MQTT down) | Log ERROR; setter returns False | Caller decides retry |
| Malformed JSON on a message | Caught in `MqttClient._on_message`; WARNING logged; message dropped | Single bad message must not break the stream |
| `deep_merge` type mismatch | Caught in helper; WARNING with path; existing value kept | Defensive; capability files may surprise us |
| Credential expiry mid-session | Reconnect loop catches SignatureDoesNotMatch / 403; refreshes credentials | see Reconnect |
| Exception in `_attr_changed` callback | Caught in base callback fanout; ERROR logged; other callbacks still fire | One bad consumer must not break the rest |
| Exception in a message handler coroutine | Caught in `MqttClient._dispatch_loop`; ERROR logged; loop continues | Dispatch loop must stay alive |

**What we do not do:**

- No automatic command retries. If `start_cook` fails because MQTT is disconnected, we return False and let callers retry.
- No circuit breakers. Too much structure for the failure modes we actually have.
- No custom exception hierarchy beyond `AuthException` (existing) and `CapabilityDownloadError` (new, internal to the downloader).
- No silent recovery from paho thread failures. If the paho thread dies, the connection is dead and the reconnect loop takes over.

### Logging discipline

- **DEBUG** — every MQTT publish/subscribe, every capability cache hit/miss, every state merge operation.
- **INFO** — connect lifecycle milestones (MQTT connected, N things discovered, N appliances registered), empty TS device list.
- **WARNING** — per-appliance skips, timeouts, unmatched capability profiles, feature-not-present command attempts.
- **ERROR** — auth failures, MQTT connect failures, malformed messages, callback exceptions.

Every log line includes the `said` when one is in scope. Contributors debugging a specific device can grep.

## Testing

Tests live in `tests/awsiot/` mirroring the production layout. Async by default (`asyncio_mode = auto` is already set in `pytest.ini`). `basedpyright` and `ruff check` must pass on every new file.

### Fixtures (`tests/awsiot/conftest.py`)

```python
@pytest.fixture
def fake_mqtt() -> FakeMqttClient: ...

@pytest.fixture
def capability_mwo() -> CapabilityProfile: ...

@pytest.fixture
def thing_mwo() -> dict: ...

@pytest.fixture
def state_mwo_full() -> dict: ...

@pytest.fixture
def state_mwo_cooking() -> dict: ...

@pytest.fixture
def aws_auth(mocker) -> Auth: ...

@pytest.fixture
async def microwave(fake_mqtt, capability_mwo, thing_mwo) -> Microwave: ...
```

### `FakeMqttClient`

The testing workhorse. Implements the same public interface as `MqttClient` (`connect`, `subscribe`, `unsubscribe`, `publish`, `add_message_handler`, `add_connection_handler`, `client_id`, `is_connected`) but backs everything with in-memory state:

- `published: list[tuple[str, dict]]` — captures every publish for assertions.
- `subscriptions: set[str]` — captures subscription state.
- `async def inject(topic: str, payload: dict) -> None` — fires registered handlers as if a message arrived.
- `async def simulate_disconnect() / simulate_reconnect()` — drives the reconnect handler path.
- No paho dependency, no threads, no event loop scheduling other than directly awaiting handlers.

This is how tests simulate state updates, command responses, presence changes, and reconnects.

### Test files

**`test_mqttclient.py`** — the only file that touches real paho. Uses `unittest.mock.patch` on `paho.mqtt.client.Client`. Covers:

- `connect()` builds the signed URL, calls `client.connect()` in an executor, waits for the connected event.
- `publish()` awaits and returns when paho's internal queue accepts the message.
- Messages arriving on the paho thread are marshalled to the dispatch loop via `call_soon_threadsafe` (verified by registering a handler and asserting it runs on the test's event loop).
- Reconnect loop backs off correctly and re-subscribes after reconnect.
- Exceptions in message handlers do not break the dispatch loop.

**`test_capabilities.py`**

- `CapabilityDownloader.get()` publishes to the right topic, subscribes to the right response topic, resolves when the injected response arrives, unsubscribes after.
- In-memory cache hit returns without publishing.
- Disk cache hit returns without publishing.
- Timeout raises `CapabilityDownloadError`.
- Parser handles the real captured `capability_mwo.json` fixture and produces a `CapabilityProfile` with expected `features` / `addressees` / `commands`.
- Parser handles a truncated/malformed capability file gracefully (raises, doesn't crash).

**`test_factory.py`**

- Registration via decorator adds to `DEFAULT_FACTORY`.
- `build()` returns the highest-priority matching class.
- `build()` returns None when nothing matches.
- Equal-priority tie: first-registered wins, WARNING logged.

**`test_matchers.py`**

- `has_addressee`, `has_feature`, `has_command`, `model_prefix`, `thing_category` — one positive and one negative case each against `capability_mwo` and `thing_mwo`.
- `all_of`, `any_of`, `not_` combinators with nested matchers.

**`test_appliance_base.py`**

- `_get_path` returns None for missing keys, handles nested dicts, rejects non-dict intermediates.
- `_get_path_bool` / `_get_path_int` / `_get_path_str` / `_get_path_float` coerce correctly and return None on type mismatch.
- `deep_merge` with nested dicts, empty updates, type mismatches, list values.
- `_send_command` publishes a well-formed payload with valid UUID and millisecond timestamp.
- `fetch_data()` resolves on state arrival, returns False on timeout.
- Presence topics update `_online`.
- Reconnect handler re-runs `fetch_data`.
- Exception in a callback is caught; other callbacks still fire.

**`test_appliancesmanager.py`**

- Happy path: fake `Things` returns one thing, fake downloader returns `capability_mwo`, factory builds a `Microwave`, it is registered under `_microwaves`.
- Empty things list returns True, registers nothing.
- `Things.list_things()` raising returns False.
- Per-appliance error isolation: two things, first one's capability download raises — second one still registers.
- Unknown capability profile (no matcher) logs WARNING, registers nothing for that thing.
- `disconnect()` unsubscribes all topics and stops the MQTT client cleanly.

**`test_microwave.py`** — the biggest test file.

- **State parsing.** Inject `state_mwo_full`, assert every getter returns the expected value. One assertion per ABC getter.
- **State delta merge.** Inject full state, then inject `{primaryCavity: {cavityLight: true}}`, assert cavity light flipped but all other fields unchanged. Deep-merge regression.
- **Callback fanout.** Register callback, inject state update, assert callback called exactly once.
- **Commands.** Call each setter/action, assert `fake_mqtt.published` contains the expected topic and payload structure. Verify `requestId` is a valid UUID, `timestamp` is plausible, `payload.addressee` and `payload.command` match.
- **Validation.** `start_cook` with power_level 0 raises ValueError. duration 0 raises ValueError. `remote_start_enabled=False` returns False and publishes nothing.
- **Feature gating.** A capability profile without hood support → `get_hood_fan_speed()` returns None, `set_hood_fan_speed(...)` returns False and logs WARNING. Requires a second capability fixture without hood features (captured from a non-over-range MWO if available, or hand-edited from `capability_mwo.json`).
- **Presence.** Inject connected → `get_online() == True`. Disconnected → False.
- **Reconnect.** Simulate disconnect + reconnect via fake client, verify microwave re-requests state (published contains `getState` after reconnect).

**`test_integration_microwave.py`**

- End-to-end: `AwsAppliancesManager` wired with `FakeMqttClient`, stubbed `Things` returning one thing, stubbed `CapabilityDownloader` returning `capability_mwo`. Walk through `connect() → getState → state update → command → callback`. One test asserting the whole chain works without touching any real network.

### Fixtures to capture from the real device

Before writing `test_microwave.py`, capture four fixtures from the KitchenAid microwave using a small capture helper (likely an enhancement of `tools/kitchenaid_iot.py` or a new `tools/capture_mwo_fixtures.py`):

1. **`thing_describe_mwo.json`** — raw DescribeThing REST response.
2. **`capability_mwo.json`** — raw capability file as returned from the download URL.
3. **`state_mwo_full.json`** — full `getState` response while the microwave is idle with hood and door closed.
4. **`state_mwo_cooking.json`** — `getState` response while actively cooking at a known power level and time.

These files are the ground truth. Every assertion in `test_microwave.py` is traceable to a field in one of these. Capturing happens in-band with implementation: writing `CapabilityDownloader` requires a real capability file to parse, so the first implementation task is the capture script.

## Development & delivery

### Source control workflow

**Local branch** — already done at spec-writing time:

```
git checkout -b aws_iot-scaffolding origin/aws_iot
```

**Fork setup** — when ready to push:

1. Fork `abmantis/whirlpool-sixth-sense` to the user's GitHub account via the web UI.
2. Add the fork as a second remote (keep `origin` pointing at abmantis for upstream updates):
   ```
   git remote add fork git@github.com:<your-user>/whirlpool-sixth-sense.git
   git push -u fork aws_iot-scaffolding
   ```
3. All commits live on `fork/aws_iot-scaffolding`. Never push to `origin/*`.

### Delivery sequence

The user explicitly asked to validate against the real device **before** publishing a draft PR. The sequence is:

1. **Fork + branch setup** (no public PR yet).
2. **Capture fixtures from the real device** (see Testing § "Fixtures to capture from the real device").
3. **Implement components on the branch**, pushing commits freely to `fork/aws_iot-scaffolding`.
4. **Run unit tests**; iterate until green. `basedpyright` and `ruff` must also pass.
5. **Wire the HACS trial integration to the fork + branch** (see "HACS trial integration" below).
6. **Walk through the real-device validation checklist** (see "Real-device validation checklist" below) against the actual microwave. Each item must check out.
7. **Only then** open the draft PR against `abmantis:aws_iot`, with the validation checklist already mostly ticked.
8. Mention abmantis in the PR body to ensure notification.
9. Respond to review feedback; mark ready for review when done.

The first public surface abmantis sees is already known to work end-to-end. Reviewer attention stays on architecture and style rather than "does this actually run."

### HACS trial integration

For using the library from Home Assistant while iterating:

1. Fork the HA integration that depends on `whirlpool-sixth-sense`.
2. Change its `manifest.json` requirement from the PyPI package to a git URL pinned to the fork + branch:
   ```json
   "requirements": ["whirlpool-sixth-sense @ git+https://github.com/<your-user>/whirlpool-sixth-sense.git@aws_iot-scaffolding"]
   ```
3. Install that integration fork as a HACS custom repository.
4. On every push to `fork/aws_iot-scaffolding`, HA picks up the change on the next integration (or full HA) restart.

**Caveat.** HA caches wheels aggressively. If a commit does not seem to take effect, clear `/config/deps/` or the HA venv's package cache.

### Commit granularity

Small, reviewable commits following abmantis's conventional-commits style. Suggested order:

1. `refactor(awsiot): make MqttClient async-safe`
2. `feat(awsiot): add CapabilityDownloader and profile parser (#122)`
3. `feat(awsiot): add ApplianceFactory and matcher helpers`
4. `refactor(awsiot): slim Appliance base class, add _get_path helpers`
5. `feat(awsiot): add stubs for Aircon/Dryer/Washer/Oven/Refrigerator`
6. `feat: add top-level Microwave ABC`
7. `feat(awsiot): implement Microwave for KitchenAid MWO`
8. `refactor(awsiot): rewrite AppliancesManager to use factory + capability download`
9. `test(awsiot): add fixtures, FakeMqttClient, and unit coverage`
10. `docs: add AWS IoT scaffolding design doc`

### Real-device validation checklist

Before opening the draft PR, exercise the microwave through the library (via an enhanced `cli.py` menu or a throwaway script) and confirm:

- [ ] Library discovers the microwave on `connect()`
- [ ] Initial state populates; all getters return plausible values
- [ ] Cavity light toggles on/off
- [ ] Hood light cycles through all four levels
- [ ] Hood light color changes through all three colors
- [ ] Hood fan cycles through all five speeds
- [ ] Starting a 30-second microwave cook at 50% power works; state transitions idle → cooking → completed
- [ ] Cancel mid-cook works; state transitions cooking → idle
- [ ] Physical door open/close reflects in `get_door_status()`
- [ ] Unplugging the microwave flips `get_online()` to False within ~10s via presence topic
- [ ] Plugging back in flips it to True and auto-fetches fresh state

The checklist goes in the PR body and gets ticked off before the PR moves out of draft.

### Draft PR body template

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
- Test fixtures and full unit coverage for the AWS path

Architecture mirrors the existing `httpapi/` layout. The goal is to keep
the external API stable across transports, matching @abmantis's stated
direction in #117.

### Design doc
See `docs/superpowers/specs/2026-04-11-aws-iot-scaffolding-design.md`.

### Real-device validation
[ … checklist pre-filled with ticks from local validation … ]

cc @abmantis — would love your thoughts on the factory/matcher pattern
and whether the Microwave ABC shape looks right.
```

## Open questions & future work

- **EMEA region routing.** `AWS_REGION = "us-east-2"` is hardcoded. A follow-up should route region through `BackendSelector` so EU accounts work.
- **Capability file format details.** The parser is provisional and will be finalized against the first captured fixture from the KitchenAid MWO. If the structure varies across models/brands, the parser may need revision — `CapabilityProfile` stays stable because it exposes only normalized fields.
- **Contributor-facing documentation.** After this lands, a short "How to add an AWS-side appliance type" doc in `docs/` would help contributors pick up the stubs. Not in scope for this PR.
- **Per-command requestId correlation.** Not implemented. Add if a consumer needs explicit acknowledgments.
- **Capability-driven feature advertisement on the ABC.** Not adding `feature_supported(name)` to the ABC in this pass; consumers use `appliance.capability_profile.has_addressee(name)` directly. Revisit if usage shows the indirection is painful.
- **Oven/MWO disambiguation edge cases.** If a real oven carries a `microwaveOven` feature flag (e.g., an oven with microwave mode), our matcher misroutes it. The priority system gives us room to fix this with an additional matcher clause without a redesign.
