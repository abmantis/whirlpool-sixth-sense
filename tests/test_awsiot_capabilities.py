"""Unit tests for the AWS IoT capability profile parser and downloader."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import aiohttp
import pytest
from aioresponses import aioresponses

from whirlpool.awsiot.capabilities import (
    CapabilityDownloader,
    CapabilityDownloadError,
    CapabilityProfile,
    parse_capability_profile,
)


class TestParserFixtureSchema:
    """The simpler schema used in our own JSON test fixtures."""

    def test_minimal_fixture(self) -> None:
        profile = parse_capability_profile(
            {
                "capabilityPartNumber": "W11111111",
                "features": ["microwaveOven", "hoodFan"],
                "addressees": {
                    "primaryCavity": ["set"],
                    "hoodFan": ["set"],
                },
            }
        )
        assert profile.part_number == "W11111111"
        assert profile.has_feature("microwaveOven")
        assert profile.has_feature("hoodFan")
        assert not profile.has_feature("turbojet")
        assert profile.has_addressee("primaryCavity")
        assert profile.has_addressee("hoodFan")
        assert not profile.has_addressee("nonsense")
        assert profile.supports_command("primaryCavity", "set")
        assert not profile.supports_command("primaryCavity", "launch")

    def test_missing_part_number_raises(self) -> None:
        with pytest.raises(CapabilityDownloadError):
            parse_capability_profile({"features": ["microwaveOven"]})

    def test_empty_part_number_raises(self) -> None:
        with pytest.raises(CapabilityDownloadError):
            parse_capability_profile({"capabilityPartNumber": ""})


class TestParserRealDeviceSchema:
    """The schema that Whirlpool's capability files actually use."""

    def test_real_device_microwave_profile(self) -> None:
        raw = {
            "partNumber": "W10000001",
            "appliance": {
                "features": {
                    "microwaveOven": {"supported": True},
                    "hoodVent": {"supported": True},
                },
            },
            "cavities": {
                "primaryCavity": {"commands": ["set", "run", "cancel"]},
            },
            "hoodFan": {"commands": ["set"]},
            "hoodLight": {"commands": ["set"]},
        }
        profile = parse_capability_profile(raw)
        assert profile.part_number == "W10000001"
        assert profile.has_feature("microwaveOven")
        assert profile.has_feature("hoodVent")
        assert profile.has_addressee("primaryCavity")
        assert profile.has_addressee("hoodFan")
        assert profile.has_addressee("hoodLight")
        assert profile.supports_command("primaryCavity", "run")
        assert not profile.supports_command("primaryCavity", "launch")

    def test_real_device_oven_profile_no_microwave_feature(self) -> None:
        """A cooking-category Oven profile should NOT have microwaveOven."""
        raw = {
            "partNumber": "W20000002",
            "appliance": {"features": {"oven": {"supported": True}}},
            "cavities": {"primaryCavity": {"commands": ["set"]}},
        }
        profile = parse_capability_profile(raw)
        assert not profile.has_feature("microwaveOven")
        assert profile.has_feature("oven")


class TestProfileIsHashable:
    """Frozen dataclass — should be usable in sets/dict keys."""

    def test_profile_equality(self) -> None:
        a = CapabilityProfile(
            part_number="X1",
            features=frozenset(),
            addressees=frozenset(),
            commands={},
        )
        b = CapabilityProfile(
            part_number="X1",
            features=frozenset(),
            addressees=frozenset(),
            commands={},
        )
        assert a == b


SAID = "SAID-1"
MODEL = "MODEL-A"
PART = "W1111"
REQ_TOPIC = f"api/capability/download/{MODEL}/{SAID}"
RESP_TOPIC = f"{REQ_TOPIC}/response"
CAP_URL = "https://caps.example.com/profile.json"
FIXTURE_JSON = {
    "capabilityPartNumber": PART,
    "features": ["microwaveOven"],
    "addressees": {"primaryCavity": ["set"]},
}


class FakeMqttClient:
    """Minimal MQTT stand-in: records publish/subscribe calls."""

    def __init__(self) -> None:
        self.published: list[tuple[str, dict[str, Any]]] = []
        self.subscribed: list[str] = []
        self.unsubscribed: list[str] = []

    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        self.published.append((topic, payload))

    def subscribe(self, topic: str) -> None:
        self.subscribed.append(topic)

    def unsubscribe(self, topic: str) -> None:
        self.unsubscribed.append(topic)


@pytest.fixture
async def http_session():
    session = aiohttp.ClientSession()
    yield session
    await session.close()


@pytest.fixture
def aio_mock():
    with aioresponses() as m:
        yield m


class TestHandleMessageDispatch:
    """handle_message() routes incoming MQTT messages to pending futures."""

    async def test_returns_false_for_unknown_topic(
        self, http_session: aiohttp.ClientSession
    ) -> None:
        downloader = CapabilityDownloader(FakeMqttClient(), http_session)
        assert downloader.handle_message("random/topic", {"x": 1}) is False

    async def test_delivers_to_pending_future(
        self, http_session: aiohttp.ClientSession, aio_mock: aioresponses
    ) -> None:
        mqtt = FakeMqttClient()
        downloader = CapabilityDownloader(mqtt, http_session, timeout=2.0)
        aio_mock.get(CAP_URL, body=json.dumps(FIXTURE_JSON))

        async def respond() -> None:
            # give get() a chance to subscribe/publish before we inject
            for _ in range(50):
                if mqtt.published:
                    break
                await asyncio.sleep(0)
            consumed = downloader.handle_message(RESP_TOPIC, {"url": CAP_URL})
            assert consumed is True

        _, profile = await asyncio.gather(
            respond(),
            downloader.get(SAID, MODEL, PART),
        )
        assert profile.part_number == PART
        assert len(mqtt.published) == 1
        topic, payload = mqtt.published[0]
        assert topic == REQ_TOPIC
        assert payload["capabilityPartNumber"] == PART
        assert "requestId" in payload
        assert RESP_TOPIC in mqtt.subscribed
        assert RESP_TOPIC in mqtt.unsubscribed


class TestDownloaderCache:
    async def test_second_call_hits_cache(
        self, http_session: aiohttp.ClientSession, aio_mock: aioresponses
    ) -> None:
        mqtt = FakeMqttClient()
        downloader = CapabilityDownloader(mqtt, http_session, timeout=2.0)
        aio_mock.get(CAP_URL, body=json.dumps(FIXTURE_JSON))

        async def respond_once() -> None:
            for _ in range(50):
                if mqtt.published:
                    break
                await asyncio.sleep(0)
            downloader.handle_message(RESP_TOPIC, {"url": CAP_URL})

        _, first = await asyncio.gather(
            respond_once(), downloader.get(SAID, MODEL, PART)
        )
        second = await downloader.get("SAID-2", MODEL, PART)

        assert first is second
        assert len(mqtt.published) == 1  # no second request


class TestDownloaderRetry:
    async def test_retries_on_timeout_then_succeeds(
        self, http_session: aiohttp.ClientSession, aio_mock: aioresponses
    ) -> None:
        mqtt = FakeMqttClient()
        downloader = CapabilityDownloader(
            mqtt, http_session, timeout=0.05, retries=3
        )
        aio_mock.get(CAP_URL, body=json.dumps(FIXTURE_JSON))

        async def respond_on_third() -> None:
            while len(mqtt.published) < 3:
                await asyncio.sleep(0.01)
            downloader.handle_message(RESP_TOPIC, {"url": CAP_URL})

        _, profile = await asyncio.gather(
            respond_on_third(), downloader.get(SAID, MODEL, PART)
        )
        assert profile.part_number == PART
        assert len(mqtt.published) == 3

    async def test_raises_after_exhausting_retries(
        self, http_session: aiohttp.ClientSession
    ) -> None:
        mqtt = FakeMqttClient()
        downloader = CapabilityDownloader(
            mqtt, http_session, timeout=0.01, retries=2
        )
        with pytest.raises(CapabilityDownloadError):
            await downloader.get(SAID, MODEL, PART)
        assert len(mqtt.published) == 2


class TestDownloaderFetchBody:
    async def test_http_error_is_download_error(
        self, http_session: aiohttp.ClientSession, aio_mock: aioresponses
    ) -> None:
        mqtt = FakeMqttClient()
        downloader = CapabilityDownloader(
            mqtt, http_session, timeout=1.0, retries=1
        )
        aio_mock.get(CAP_URL, status=500)

        async def respond() -> None:
            for _ in range(50):
                if mqtt.published:
                    break
                await asyncio.sleep(0)
            downloader.handle_message(RESP_TOPIC, {"url": CAP_URL})

        with pytest.raises(CapabilityDownloadError):
            await asyncio.gather(respond(), downloader.get(SAID, MODEL, PART))

    async def test_inline_payload_without_url(
        self, http_session: aiohttp.ClientSession
    ) -> None:
        """If the MQTT response already contains the profile body, skip HTTP."""
        mqtt = FakeMqttClient()
        downloader = CapabilityDownloader(
            mqtt, http_session, timeout=1.0, retries=1
        )

        async def respond() -> None:
            for _ in range(50):
                if mqtt.published:
                    break
                await asyncio.sleep(0)
            downloader.handle_message(RESP_TOPIC, FIXTURE_JSON)

        _, profile = await asyncio.gather(
            respond(), downloader.get(SAID, MODEL, PART)
        )
        assert profile.part_number == PART
