"""Unit tests for the AWS IoT capability profile parser and downloader."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import aiohttp
import pytest
from aioresponses import aioresponses

from whirlpool.awsiot.capabilities import (
    CapabilityDownloader,
    CapabilityDownloadError,
    has_microwave_cavity,
    parse_microwave_capability_profile,
)

DATA_DIR = Path(__file__).parent / "data"


def _load(name: str) -> dict[str, Any]:
    return json.loads((DATA_DIR / name).read_text())


class TestParseMicrowaveCapability:
    def test_microwave_with_hood(self) -> None:
        profile = parse_microwave_capability_profile(_load("capability_mwo.json"))
        assert profile.part_number == "W11788386"
        assert profile.supports_hood_fan
        assert profile.supports_hood_light_level
        assert profile.supports_hood_light_color
        assert profile.supports_quiet_mode
        assert not profile.supports_control_lock
        assert not profile.supports_sabbath_mode

    def test_microwave_without_hood(self) -> None:
        profile = parse_microwave_capability_profile(
            _load("capability_mwo_no_hood.json")
        )
        assert profile.part_number == "W11650001"
        assert not profile.supports_hood_fan
        assert not profile.supports_hood_light_level
        assert not profile.supports_hood_light_color
        assert profile.supports_quiet_mode

    def test_sabbath_recipes_mark_sabbath_supported(self) -> None:
        profile = parse_microwave_capability_profile(
            {
                "partNumber": "X1",
                "cavities": {
                    "primaryCavity": {
                        "cavityType": "microwaveOven",
                        "sabbathRecipes": {"sabbath": {}},
                    }
                },
            }
        )
        assert profile.supports_sabbath_mode

    @pytest.mark.parametrize(
        "raw",
        [{"appliance": {"features": {}}}, {"partNumber": ""}],
    )
    def test_invalid_part_number_raises(self, raw: dict[str, Any]) -> None:
        with pytest.raises(CapabilityDownloadError):
            parse_microwave_capability_profile(raw)

    def test_tolerates_odd_substructures(self) -> None:
        profile = parse_microwave_capability_profile(
            {"partNumber": "X1", "appliance": "nope", "cavities": [1, 2]}
        )
        assert profile.part_number == "X1"
        assert not profile.supports_hood_fan
        assert not profile.supports_quiet_mode
        assert not profile.supports_sabbath_mode

    def test_profile_equality_is_value_based(self) -> None:
        raw = _load("capability_mwo.json")
        assert parse_microwave_capability_profile(
            raw
        ) == parse_microwave_capability_profile(json.loads(json.dumps(raw)))


class TestHasMicrowaveCavity:
    @pytest.mark.parametrize(
        "fixture", ["capability_mwo.json", "capability_mwo_no_hood.json"]
    )
    def test_real_microwave_files(self, fixture: str) -> None:
        assert has_microwave_cavity(_load(fixture))

    def test_oven_cavity(self) -> None:
        assert not has_microwave_cavity(
            {"cavities": {"primaryCavity": {"cavityType": "oven"}}}
        )

    @pytest.mark.parametrize(
        "raw",
        [{}, {"cavities": [1, 2]}, {"cavities": {"primaryCavity": "nope"}}],
    )
    def test_tolerates_odd_substructures(self, raw: dict[str, Any]) -> None:
        assert not has_microwave_cavity(raw)


SAID = "SAID-1"
MODEL = "MODEL-A"
PART = "W1111"
REQ_TOPIC = f"api/capability/download/{MODEL}/{SAID}"
RESP_TOPIC = f"{REQ_TOPIC}/response"
CAP_URL = "https://caps.example.com/profile.json"
FIXTURE_JSON = {
    "partNumber": PART,
    "appliance": {"features": {"microwaveOven": {}}},
    "cavities": {"primaryCavity": {"cavityType": "microwaveOven"}},
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
        self,
        http_session: aiohttp.ClientSession,
        aio_mock: aioresponses,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "whirlpool.awsiot.capabilities.CAPABILITY_DOWNLOAD_TIMEOUT", 2.0
        )
        mqtt = FakeMqttClient()
        downloader = CapabilityDownloader(mqtt, http_session)
        aio_mock.get(CAP_URL, body=json.dumps(FIXTURE_JSON))

        async def respond() -> None:
            # give get() a chance to subscribe/publish before we inject
            for _ in range(50):
                if mqtt.published:
                    break
                await asyncio.sleep(0)
            consumed = downloader.handle_message(RESP_TOPIC, {"url": CAP_URL})
            assert consumed is True

        _, raw = await asyncio.gather(
            respond(),
            downloader.get(SAID, MODEL, PART),
        )
        assert raw["partNumber"] == PART
        assert len(mqtt.published) == 1
        topic, payload = mqtt.published[0]
        assert topic == REQ_TOPIC
        assert payload["capabilityPartNumber"] == PART
        assert "requestId" in payload
        assert RESP_TOPIC in mqtt.subscribed
        assert RESP_TOPIC in mqtt.unsubscribed


class TestDownloaderCache:
    async def test_second_call_hits_cache(
        self,
        http_session: aiohttp.ClientSession,
        aio_mock: aioresponses,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "whirlpool.awsiot.capabilities.CAPABILITY_DOWNLOAD_TIMEOUT", 2.0
        )
        mqtt = FakeMqttClient()
        downloader = CapabilityDownloader(mqtt, http_session)
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
        self,
        http_session: aiohttp.ClientSession,
        aio_mock: aioresponses,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "whirlpool.awsiot.capabilities.CAPABILITY_DOWNLOAD_TIMEOUT", 0.05
        )
        monkeypatch.setattr(
            "whirlpool.awsiot.capabilities.CAPABILITY_DOWNLOAD_RETRIES", 3
        )
        mqtt = FakeMqttClient()
        downloader = CapabilityDownloader(mqtt, http_session)
        aio_mock.get(CAP_URL, body=json.dumps(FIXTURE_JSON))

        async def respond_on_third() -> None:
            while len(mqtt.published) < 3:
                await asyncio.sleep(0.01)
            downloader.handle_message(RESP_TOPIC, {"url": CAP_URL})

        _, raw = await asyncio.gather(
            respond_on_third(), downloader.get(SAID, MODEL, PART)
        )
        assert raw["partNumber"] == PART
        assert len(mqtt.published) == 3

    async def test_raises_after_exhausting_retries(
        self, http_session: aiohttp.ClientSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "whirlpool.awsiot.capabilities.CAPABILITY_DOWNLOAD_TIMEOUT", 0.01
        )
        monkeypatch.setattr(
            "whirlpool.awsiot.capabilities.CAPABILITY_DOWNLOAD_RETRIES", 2
        )
        mqtt = FakeMqttClient()
        downloader = CapabilityDownloader(mqtt, http_session)
        with pytest.raises(CapabilityDownloadError):
            await downloader.get(SAID, MODEL, PART)
        assert len(mqtt.published) == 2


class TestDownloaderFetchBody:
    async def test_http_error_is_download_error(
        self,
        http_session: aiohttp.ClientSession,
        aio_mock: aioresponses,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "whirlpool.awsiot.capabilities.CAPABILITY_DOWNLOAD_TIMEOUT", 1.0
        )
        monkeypatch.setattr(
            "whirlpool.awsiot.capabilities.CAPABILITY_DOWNLOAD_RETRIES", 1
        )
        mqtt = FakeMqttClient()
        downloader = CapabilityDownloader(mqtt, http_session)
        aio_mock.get(CAP_URL, status=500)

        async def respond() -> None:
            for _ in range(50):
                if mqtt.published:
                    break
                await asyncio.sleep(0)
            downloader.handle_message(RESP_TOPIC, {"url": CAP_URL})

        with pytest.raises(CapabilityDownloadError):
            await asyncio.gather(respond(), downloader.get(SAID, MODEL, PART))

    async def test_document_without_part_number_is_download_error(
        self, http_session: aiohttp.ClientSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A response that is not a capability file must not be cached."""
        monkeypatch.setattr(
            "whirlpool.awsiot.capabilities.CAPABILITY_DOWNLOAD_TIMEOUT", 1.0
        )
        monkeypatch.setattr(
            "whirlpool.awsiot.capabilities.CAPABILITY_DOWNLOAD_RETRIES", 1
        )
        mqtt = FakeMqttClient()
        downloader = CapabilityDownloader(mqtt, http_session)

        async def respond() -> None:
            for _ in range(50):
                if mqtt.published:
                    break
                await asyncio.sleep(0)
            downloader.handle_message(RESP_TOPIC, {"unexpected": "payload"})

        with pytest.raises(CapabilityDownloadError):
            await asyncio.gather(respond(), downloader.get(SAID, MODEL, PART))

        # The bogus document must not have been cached: a later get() issues a
        # fresh request instead of serving the bad payload.
        async def respond_valid() -> None:
            for _ in range(50):
                if len(mqtt.published) >= 2:
                    break
                await asyncio.sleep(0)
            downloader.handle_message(RESP_TOPIC, FIXTURE_JSON)

        _, raw = await asyncio.gather(
            respond_valid(), downloader.get(SAID, MODEL, PART)
        )
        assert raw["partNumber"] == PART
        assert len(mqtt.published) == 2

    async def test_inline_payload_without_url(
        self, http_session: aiohttp.ClientSession, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If the MQTT response already contains the profile body, skip HTTP."""
        monkeypatch.setattr(
            "whirlpool.awsiot.capabilities.CAPABILITY_DOWNLOAD_TIMEOUT", 1.0
        )
        monkeypatch.setattr(
            "whirlpool.awsiot.capabilities.CAPABILITY_DOWNLOAD_RETRIES", 1
        )
        mqtt = FakeMqttClient()
        downloader = CapabilityDownloader(mqtt, http_session)

        async def respond() -> None:
            for _ in range(50):
                if mqtt.published:
                    break
                await asyncio.sleep(0)
            downloader.handle_message(RESP_TOPIC, FIXTURE_JSON)

        _, raw = await asyncio.gather(
            respond(), downloader.get(SAID, MODEL, PART)
        )
        assert raw["partNumber"] == PART
