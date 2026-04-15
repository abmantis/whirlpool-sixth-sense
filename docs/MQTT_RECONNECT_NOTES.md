# MQTT reconnect — port notes

Fix lives on `aws_iot-scaffolding` in `whirlpool/awsiot/mqttclient.py`. Needs
to be ported to any other branch that ships `MqttClient` (abmantis's
`aws_iot` base, our stacked PRs `aws-iot-microwave-pr1` → `aws-iot-cook-pr4`,
and eventually upstream if a `MicrowaveOven` PR lands).

## The bug

`_on_disconnect` logged the failure, cleared state, and fired listener
handlers — and that was it. No reconnect. Paho's own auto-reconnect can't
save us because `connect()` installs a SigV4-signed websocket URL via
`ws_set_options(path=...)`; any reused signature eventually expires. Real
symptom observed on `cuteredhouse` 2026-04-14: a single `MQTT unexpected
disconnect: Unspecified error` at 19:05 CDT → all microwave entities went
`unavailable` ~20 min later → 683 "Cannot publish" + 683 "Timed out
waiting for initial state" warnings over the next 12 h. Never recovered
until HA restart.

## The fix (shape)

In `whirlpool/awsiot/mqttclient.py`:

1. **Module constant** `RECONNECT_BACKOFF_INITIAL_SECONDS = 1.0` alongside
   the existing `RECONNECT_BACKOFF_CAP_SECONDS = 30.0` (previously dead).
2. **Instance state** in `__init__`: `_reconnect_task: asyncio.Task | None`
   and `_shutting_down: bool`.
3. **`_on_disconnect`**: if `reason_code.is_failure`, call
   `self._loop.call_soon_threadsafe(self._schedule_reconnect)` after
   clearing `_connected` and firing disconnect handlers.
4. **`_schedule_reconnect`**: no-op if `_shutting_down` or if a live
   reconnect task already exists; otherwise `create_task(self._reconnect_loop())`.
5. **`_reconnect_loop`**: exponential backoff starting at
   `RECONNECT_BACKOFF_INITIAL_SECONDS`, doubling, capped at
   `RECONNECT_BACKOFF_CAP_SECONDS`. Each iteration stops the old paho
   client's network loop (best-effort, swallow errors) and calls
   `await self.connect()`. `connect()` already fetches a fresh signed URL,
   so re-auth happens transparently. Exit on success or cancellation.
6. **`connect()`**: guard `_dispatch_task` recreation with
   `if self._dispatch_task is None or self._dispatch_task.done()` so
   multiple reconnects don't spawn duplicate dispatch loops.
7. **`disconnect()`**: set `_shutting_down = True` first, then cancel and
   await `_reconnect_task` before the existing teardown.

## Tests (`tests/awsiot/test_mqttclient.py::TestReconnect`)

Three:
- `test_unexpected_disconnect_rebuilds_client_and_resubscribes` — happy
  path. Patches `mqtt.Client` with a factory that records every instance;
  fires failure disconnect; asserts a new paho client is built, a fresh
  signed URL was requested, and prior subscriptions reapply on the new
  client.
- `test_clean_disconnect_does_not_trigger_reconnect` — fires
  `is_failure=False`; asserts no fresh URL fetch and no reconnect.
- `test_explicit_disconnect_cancels_pending_reconnect` — uses a 60s backoff
  so the reconnect task is still sleeping; calls `disconnect()`; asserts the
  task is cancelled and no second paho client was built.

Test pattern borrows from the existing `_build_client` helper but uses a
`paho_factory` closure that tracks every instance, and monkeypatches
`RECONNECT_BACKOFF_INITIAL_SECONDS` to `0.0` to skip waiting.

## Porting order (when ready)

1. **`aws-iot-microwave-pr1`** — the MQTT client on abmantis's `aws_iot`
   base is identical to scaffolding's (scaffolding was rebased onto it).
   Should cherry-pick cleanly. Port tests too.
2. **Later stacked PRs** — they inherit the fix once PR1 lands. Re-run
   `tests/awsiot/test_mqttclient.py` on each.
3. **Upstream PR to abmantis** — separate PR targeted at `aws_iot`, not
   part of the microwave feature chain. Title suggestion: *"AWS IoT: auto-
   reconnect MQTT client after unexpected disconnect"*. Body should
   reference the `cuteredhouse` incident as evidence of the gap.

## Don't forget

- Two pre-existing HA warnings about blocking TLS calls
  (`load_default_certs`, `set_default_verify_paths`) at `mqttclient.py:88`
  — **not fixed here**. Separate issue; move `client.tls_set(...)` into a
  `run_in_executor` if/when we address it.
- `RECONNECT_BACKOFF_CAP_SECONDS` was dead before this fix; ensure the
  port keeps it as the cap for the doubling backoff.
