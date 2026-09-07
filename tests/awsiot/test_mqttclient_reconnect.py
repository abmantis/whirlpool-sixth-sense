"""Tests for MqttClient auto-reconnect on unexpected disconnect.

The real-world failure that motivates these: a single SigV4 websocket
disconnect (roaming DHCP lease, broker-initiated drop, etc.) used to
leave the client permanently offline until the host restarted, because
paho's own auto-reconnect reuses the original signed URL, which expires.
"""

import asyncio
import logging
import threading
from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from whirlpool.awsiot.mqttclient import MqttClient

LOGGER_NAME = "whirlpool.awsiot.mqttclient"


class FakePahoClient:
    """Stand-in for `paho.mqtt.client.Client`.

    Plays the broker side: after `loop_start()` a CONNACK is delivered from a
    background thread, the same way paho's network thread would. Tests drop
    the connection with `fire_disconnect()`.
    """

    def __init__(self, connack: bool, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self._connack = connack
        self.on_connect: Any = None
        self.on_message: Any = None
        self.on_disconnect: Any = None
        self.on_subscribe: Any = None
        self.subscribed: list[str] = []
        self.loop_stopped = False
        self.disconnected = False

    def ws_set_options(self, **_kwargs: Any) -> None:
        pass

    def username_pw_set(self, **_kwargs: Any) -> None:
        pass

    def tls_set(self, **_kwargs: Any) -> None:
        pass

    def connect(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    def loop_start(self) -> None:
        if self._connack:
            threading.Thread(
                target=self.on_connect,
                args=(self, None, MagicMock(), MagicMock(is_failure=False), None),
                daemon=True,
            ).start()

    def loop_stop(self) -> None:
        self.loop_stopped = True

    def disconnect(self) -> None:
        self.disconnected = True

    def subscribe(self, topic: str, qos: int = 0) -> None:
        self.subscribed.append(topic)

    def unsubscribe(self, topic: str) -> None:
        pass

    def publish(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    def fire_disconnect(self, *, is_failure: bool) -> None:
        """Simulate the broker dropping the connection."""
        self.on_disconnect(
            self, None, MagicMock(), MagicMock(is_failure=is_failure), None
        )


class FakePaho:
    """Factory installed in place of `mqtt.Client`; keeps every built client."""

    def __init__(self) -> None:
        self.clients: list[FakePahoClient] = []
        self.connack = True

    def __call__(self, **kwargs: Any) -> FakePahoClient:
        client = FakePahoClient(self.connack, **kwargs)
        self.clients.append(client)
        return client


@pytest.fixture
def paho(monkeypatch: pytest.MonkeyPatch) -> FakePaho:
    fake = FakePaho()
    monkeypatch.setattr("whirlpool.awsiot.mqttclient.mqtt.Client", fake)
    # Collapse the backoff so the reconnect loop doesn't slow tests.
    monkeypatch.setattr(
        "whirlpool.awsiot.mqttclient.RECONNECT_BACKOFF_INITIAL_SECONDS", 0.01
    )
    return fake


@pytest.fixture
def mock_aws_auth() -> AsyncMock:
    auth = AsyncMock()
    auth.create_signed_url.return_value = (
        "wss://wt.applianceconnect.net/mqtt?X-Amz-Algorithm=fake"
    )
    auth.get_cognito_identity_id.return_value = "fake-identity-id"
    return auth


async def _wait_for(predicate: Callable[[], bool], timeout: float = 5.0) -> None:
    """Poll until `predicate` holds; the worker thread does the actual work."""
    async with asyncio.timeout(timeout):
        while not predicate():
            await asyncio.sleep(0.01)


def _logged(caplog: pytest.LogCaptureFixture, message: str) -> bool:
    return any(record.message == message for record in caplog.records)


class TestReconnect:
    async def test_unexpected_disconnect_rebuilds_client_and_resubscribes(
        self, mock_aws_auth: AsyncMock, paho: FakePaho
    ) -> None:
        """After an unexpected MQTT disconnect the client must rebuild
        itself: fetch a fresh signed URL, create a new paho client, and
        reapply all prior subscriptions. Without this, a single websocket
        drop leaves the integration permanently unavailable until the host
        restarts."""

        client = MqttClient(mock_aws_auth)
        assert await client.connect() is True
        await client.subscribe("topic/a")
        mock_aws_auth.create_signed_url.reset_mock()

        paho.clients[0].fire_disconnect(is_failure=True)
        await _wait_for(
            lambda: len(paho.clients) == 2 and "topic/a" in paho.clients[1].subscribed
        )

        assert client.is_connected()
        mock_aws_auth.create_signed_url.assert_awaited_once()

        await client.disconnect()

    async def test_successful_reconnect_uses_quiet_progress_logs(
        self,
        mock_aws_auth: AsyncMock,
        paho: FakePaho,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Retry progress and success should not flood HA warnings."""

        caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)

        client = MqttClient(mock_aws_auth)
        assert await client.connect() is True

        paho.clients[0].fire_disconnect(is_failure=True)
        await _wait_for(lambda: _logged(caplog, "MQTT reconnected successfully"))

        records = [record for record in caplog.records if record.name == LOGGER_NAME]
        warnings = [record for record in records if record.levelno >= logging.WARNING]
        assert len(warnings) == 1
        assert warnings[0].message.startswith("MQTT unexpected disconnect")
        assert any(
            record.levelno == logging.DEBUG
            and record.message.startswith("MQTT reconnecting in")
            for record in records
        )
        assert any(
            record.levelno == logging.INFO
            and record.message == "MQTT reconnected successfully"
            for record in records
        )

        await client.disconnect()

    async def test_failed_reconnect_logs_concise_warning_and_debug_traceback(
        self,
        mock_aws_auth: AsyncMock,
        paho: FakePaho,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Repeated reconnect failures should avoid warning-level tracebacks."""

        caplog.set_level(logging.DEBUG, logger=LOGGER_NAME)

        client = MqttClient(mock_aws_auth)
        assert await client.connect() is True

        mock_aws_auth.create_signed_url.side_effect = RuntimeError(
            "temporary auth failure"
        )
        paho.clients[0].fire_disconnect(is_failure=True)
        await _wait_for(
            lambda: _logged(
                caplog, "MQTT reconnect attempt failed: temporary auth failure"
            )
        )

        records = [record for record in caplog.records if record.name == LOGGER_NAME]
        assert any(
            record.levelno == logging.WARNING
            and record.message
            == "MQTT reconnect attempt failed: temporary auth failure"
            and record.exc_info is None
            for record in records
        )
        assert any(
            record.levelno == logging.DEBUG
            and record.message == "MQTT reconnect attempt traceback"
            and record.exc_info is not None
            for record in records
        )
        assert not any(
            record.levelno >= logging.WARNING and record.exc_info is not None
            for record in records
        )

        await client.disconnect()

    async def test_clean_disconnect_does_not_trigger_reconnect(
        self, mock_aws_auth: AsyncMock, paho: FakePaho
    ) -> None:
        """A clean disconnect (is_failure=False) means the broker or we
        intentionally closed the connection; don't try to reconnect."""

        client = MqttClient(mock_aws_auth)
        assert await client.connect() is True
        mock_aws_auth.create_signed_url.reset_mock()

        paho.clients[0].fire_disconnect(is_failure=False)
        await asyncio.sleep(0.1)

        mock_aws_auth.create_signed_url.assert_not_awaited()
        assert len(paho.clients) == 1
        assert not client.is_connected()

        await client.disconnect()

    async def test_reconnect_keeps_client_id_stable(
        self, mock_aws_auth: AsyncMock, paho: FakePaho
    ) -> None:
        """Reconnect must keep the same MQTT client ID.

        Appliances build response subscriptions from `client_id`. If a
        reconnect changes it, we resubscribe the old response topic but
        publish requests using the new response topic.
        """

        client = MqttClient(mock_aws_auth)
        assert await client.connect() is True
        first_client_id = client.client_id
        assert first_client_id is not None

        paho.clients[0].fire_disconnect(is_failure=True)
        await _wait_for(lambda: len(paho.clients) == 2 and client.is_connected())

        assert client.client_id == first_client_id
        assert paho.clients[1].kwargs["client_id"] == first_client_id

        await client.disconnect()

    async def test_stale_disconnect_from_old_client_is_ignored(
        self, mock_aws_auth: AsyncMock, paho: FakePaho
    ) -> None:
        """Callbacks from a replaced paho client must not affect state."""

        client = MqttClient(mock_aws_auth)
        assert await client.connect() is True

        paho.clients[0].fire_disconnect(is_failure=True)
        await _wait_for(lambda: len(paho.clients) == 2 and client.is_connected())

        paho.clients[0].fire_disconnect(is_failure=True)
        await asyncio.sleep(0.1)

        assert client.is_connected()
        assert len(paho.clients) == 2

        await client.disconnect()

    async def test_connect_reentry_tears_down_previous_client(
        self, mock_aws_auth: AsyncMock, paho: FakePaho
    ) -> None:
        """Calling connect() again must tear down the previous paho client so
        its loop thread and socket are not leaked."""

        client = MqttClient(mock_aws_auth)
        assert await client.connect() is True

        # Second connect() without a disconnect() in between.
        assert await client.connect() is True

        assert len(paho.clients) == 2
        assert paho.clients[0].loop_stopped
        assert paho.clients[0].disconnected
        assert client.is_connected()

        await client.disconnect()

    async def test_connect_timeout_disconnects_paho_client(
        self, mock_aws_auth: AsyncMock, paho: FakePaho, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """On connect timeout (no CONNACK) the paho client must be stopped and
        disconnected so we don't leave the socket/loop thread behind."""

        monkeypatch.setattr("whirlpool.awsiot.mqttclient.CONNECT_TIMEOUT_SECONDS", 0.01)
        # Never deliver CONNACK, so connect() hits the timeout path.
        paho.connack = False

        client = MqttClient(mock_aws_auth)
        assert await client.connect() is False

        assert len(paho.clients) == 1
        assert paho.clients[0].loop_stopped
        assert paho.clients[0].disconnected
        assert not client.is_connected()

        await client.disconnect()

    async def test_explicit_disconnect_stops_pending_reconnect(
        self, mock_aws_auth: AsyncMock, paho: FakePaho, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Calling disconnect() while the reconnect loop is backing off must
        stop it promptly so the caller can tear down cleanly."""

        # Use a long backoff so the reconnect loop is still waiting when we
        # call disconnect().
        monkeypatch.setattr(
            "whirlpool.awsiot.mqttclient.RECONNECT_BACKOFF_INITIAL_SECONDS", 60.0
        )

        client = MqttClient(mock_aws_auth)
        assert await client.connect() is True

        paho.clients[0].fire_disconnect(is_failure=True)
        await asyncio.sleep(0.05)

        async with asyncio.timeout(5.0):
            await client.disconnect()

        # No second paho client should have been built.
        assert len(paho.clients) == 1
        assert not client.is_connected()
        assert client.client_id is None
