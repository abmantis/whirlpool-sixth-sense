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
        client._on_message(fake_paho, None, msg)  # pyright: ignore[reportPrivateUsage]
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
        client._on_message(fake_paho, None, msg1)  # pyright: ignore[reportPrivateUsage]
        await _flush()

        msg2 = MagicMock()
        msg2.topic = "t"
        msg2.payload = b"{}"
        client._on_message(fake_paho, None, msg2)  # pyright: ignore[reportPrivateUsage]
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
        client._on_message(fake_paho, None, msg)  # pyright: ignore[reportPrivateUsage]
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
        drop leaves the integration permanently unavailable until HA
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

        await client.subscribe("topic/a")

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
        self, mock_aws_auth: AsyncMock, fake_paho: MagicMock
    ) -> None:
        """A clean disconnect (is_failure=False) means the broker or we
        intentionally closed the connection; don't try to reconnect."""
        client = await _build_client(mock_aws_auth, fake_paho)

        # Reset so we can detect any fresh URL fetch after the disconnect.
        mock_aws_auth.create_signed_url.reset_mock()

        fake_paho.on_disconnect(
            fake_paho, None, MagicMock(), MagicMock(is_failure=False), None
        )
        # Give any stray reconnect task a chance to run.
        for _ in range(10):
            await _flush()

        mock_aws_auth.create_signed_url.assert_not_called()
        assert not client.is_connected()

        await client.disconnect()

    async def test_explicit_disconnect_cancels_pending_reconnect(
        self, mock_aws_auth: AsyncMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Calling disconnect() must cancel any in-flight reconnect loop
        so HA can tear down the integration cleanly."""

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
