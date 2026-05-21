"""Tests for MqttClient auto-reconnect on unexpected disconnect.

The real-world failure that motivates these: a single SigV4 websocket
disconnect (roaming DHCP lease, broker-initiated drop, etc.) used to
leave the client permanently offline until the host restarted, because
paho's own auto-reconnect reuses the original signed URL, which expires.
"""

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


def _fire_connack(paho_instance: MagicMock) -> None:
    paho_instance.on_connect(
        paho_instance, None, MagicMock(), MagicMock(is_failure=False), None
    )


def _fire_failure_disconnect(paho_instance: MagicMock) -> None:
    paho_instance.on_disconnect(
        paho_instance, None, MagicMock(), MagicMock(is_failure=True), None
    )


class TestReconnect:
    async def test_unexpected_disconnect_rebuilds_client_and_resubscribes(
        self, mock_aws_auth: AsyncMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """After an unexpected MQTT disconnect the client must rebuild
        itself: fetch a fresh signed URL, create a new paho client, and
        reapply all prior subscriptions. Without this, a single websocket
        drop leaves the integration permanently unavailable until the host
        restarts."""

        paho_clients: list[MagicMock] = []

        def paho_factory(**_kwargs: Any) -> MagicMock:
            instance = MagicMock(name=f"paho.Client[{len(paho_clients)}]")
            instance.connect.return_value = None
            instance.publish.return_value = None
            instance.subscribe.return_value = None
            instance.unsubscribe.return_value = None
            paho_clients.append(instance)
            return instance

        monkeypatch.setattr(
            "whirlpool.awsiot.mqttclient.mqtt.Client", paho_factory
        )
        # Collapse the backoff so the reconnect loop doesn't slow tests.
        monkeypatch.setattr(
            "whirlpool.awsiot.mqttclient.RECONNECT_BACKOFF_INITIAL_SECONDS",
            0.0,
        )

        client = MqttClient(mock_aws_auth)
        connect_task = asyncio.create_task(client.connect())
        await _flush()
        _fire_connack(paho_clients[0])
        await _flush()
        assert await connect_task is True

        client.subscribe("topic/a")

        mock_aws_auth.create_signed_url.reset_mock()

        _fire_failure_disconnect(paho_clients[0])

        # Drive the reconnect to completion. We don't know exactly when
        # each await in connect() resolves, so keep flushing and firing
        # on_connect on the newest paho client until is_connected is set.
        for _ in range(100):
            await _flush()
            if client.is_connected():
                break
            if len(paho_clients) >= 2:
                _fire_connack(paho_clients[-1])

        assert len(paho_clients) >= 2, (
            f"expected reconnect to build a new paho client, got "
            f"{len(paho_clients)}"
        )
        mock_aws_auth.create_signed_url.assert_called()
        assert client.is_connected()
        paho_clients[-1].subscribe.assert_any_call("topic/a", qos=1)

        await client.disconnect()

    async def test_clean_disconnect_does_not_trigger_reconnect(
        self, mock_aws_auth: AsyncMock
    ) -> None:
        """A clean disconnect (is_failure=False) means the broker or we
        intentionally closed the connection; don't try to reconnect."""

        fake_paho = MagicMock(name="paho.Client")
        fake_paho.connect.return_value = None

        with patch(
            "whirlpool.awsiot.mqttclient.mqtt.Client", return_value=fake_paho
        ):
            client = MqttClient(mock_aws_auth)
            connect_task = asyncio.create_task(client.connect())
            await _flush()
            _fire_connack(fake_paho)
            await _flush()
            assert await connect_task is True

            mock_aws_auth.create_signed_url.reset_mock()

            fake_paho.on_disconnect(
                fake_paho, None, MagicMock(), MagicMock(is_failure=False), None
            )
            for _ in range(10):
                await _flush()

            mock_aws_auth.create_signed_url.assert_not_called()
            assert not client.is_connected()

            await client.disconnect()

    async def test_reconnect_keeps_client_id_stable(
        self, mock_aws_auth: AsyncMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Reconnect must keep the same MQTT client ID.

        Appliances build response subscriptions from `client_id`. If a
        reconnect changes it, we resubscribe the old response topic but
        publish requests using the new response topic.
        """

        paho_clients: list[MagicMock] = []

        def paho_factory(**_kwargs: Any) -> MagicMock:
            instance = MagicMock(name=f"paho.Client[{len(paho_clients)}]")
            instance.connect.return_value = None
            paho_clients.append(instance)
            return instance

        monkeypatch.setattr(
            "whirlpool.awsiot.mqttclient.mqtt.Client", paho_factory
        )
        monkeypatch.setattr(
            "whirlpool.awsiot.mqttclient.RECONNECT_BACKOFF_INITIAL_SECONDS",
            0.0,
        )

        client = MqttClient(mock_aws_auth)
        connect_task = asyncio.create_task(client.connect())
        await _flush()
        _fire_connack(paho_clients[0])
        await _flush()
        assert await connect_task is True
        first_client_id = client.client_id

        _fire_failure_disconnect(paho_clients[0])

        for _ in range(100):
            await _flush()
            if len(paho_clients) >= 2:
                _fire_connack(paho_clients[-1])
            if client.is_connected() and len(paho_clients) >= 2:
                break

        assert client.is_connected()
        assert client.client_id == first_client_id

        await client.disconnect()

    async def test_stale_disconnect_from_old_client_is_ignored(
        self, mock_aws_auth: AsyncMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Callbacks from a replaced paho client must not affect state."""

        paho_clients: list[MagicMock] = []

        def paho_factory(**_kwargs: Any) -> MagicMock:
            instance = MagicMock(name=f"paho.Client[{len(paho_clients)}]")
            instance.connect.return_value = None
            paho_clients.append(instance)
            return instance

        monkeypatch.setattr(
            "whirlpool.awsiot.mqttclient.mqtt.Client", paho_factory
        )
        monkeypatch.setattr(
            "whirlpool.awsiot.mqttclient.RECONNECT_BACKOFF_INITIAL_SECONDS",
            0.0,
        )

        client = MqttClient(mock_aws_auth)
        connect_task = asyncio.create_task(client.connect())
        await _flush()
        _fire_connack(paho_clients[0])
        await _flush()
        assert await connect_task is True

        _fire_failure_disconnect(paho_clients[0])
        for _ in range(100):
            await _flush()
            if len(paho_clients) >= 2:
                _fire_connack(paho_clients[-1])
            if client.is_connected() and len(paho_clients) >= 2:
                break

        assert client.is_connected()

        paho_clients[0].on_disconnect(
            paho_clients[0], None, MagicMock(), MagicMock(is_failure=False), None
        )
        await _flush()

        assert client.is_connected()

        await client.disconnect()

    async def test_explicit_disconnect_cancels_pending_reconnect(
        self, mock_aws_auth: AsyncMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Calling disconnect() must cancel any in-flight reconnect loop
        so the caller can tear down cleanly."""

        paho_clients: list[MagicMock] = []

        def paho_factory(**_kwargs: Any) -> MagicMock:
            instance = MagicMock(name=f"paho.Client[{len(paho_clients)}]")
            instance.connect.return_value = None
            paho_clients.append(instance)
            return instance

        monkeypatch.setattr(
            "whirlpool.awsiot.mqttclient.mqtt.Client", paho_factory
        )
        # Use a non-zero backoff so the reconnect loop is still in
        # asyncio.sleep when we call disconnect().
        monkeypatch.setattr(
            "whirlpool.awsiot.mqttclient.RECONNECT_BACKOFF_INITIAL_SECONDS",
            60.0,
        )

        client = MqttClient(mock_aws_auth)
        connect_task = asyncio.create_task(client.connect())
        await _flush()
        _fire_connack(paho_clients[0])
        await _flush()
        assert await connect_task is True

        _fire_failure_disconnect(paho_clients[0])
        for _ in range(10):
            await _flush()

        # Reconnect task should be scheduled and sleeping.
        assert client._reconnect_task is not None  # pyright: ignore[reportPrivateUsage]
        assert not client._reconnect_task.done()  # pyright: ignore[reportPrivateUsage]

        await client.disconnect()

        assert client._reconnect_task is None  # pyright: ignore[reportPrivateUsage]
        # No second paho client should have been built.
        assert len(paho_clients) == 1
