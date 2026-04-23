import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from whirlpool.awsiot.capabilities import (
    CapabilityDownloader,
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
        assert profile.part_number == "W11788386"
        assert "microwaveOven" in profile.features
        assert "hoodFan" in profile.addressees
        assert "primaryCavity" in profile.addressees
        assert profile.supports_command("primaryCavity", "microwave") is True
        assert profile.supports_command("primaryCavity", "nonesuch") is False
        assert profile.has_feature("microwaveOven") is True
        assert profile.has_addressee("hoodFan") is True

    def test_raw_preserved(self, capability_mwo_raw: dict) -> None:
        profile = parse_capability_profile(capability_mwo_raw)
        assert profile.raw == capability_mwo_raw
        assert profile.metadata.get("contentManagementProject") == "FLUSH"

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


class _FakeSession:
    """Minimal aiohttp.ClientSession stand-in for tests."""

    def __init__(self, url_to_body: dict[str, dict[str, Any]]) -> None:
        self._url_to_body = url_to_body

    def get(self, url: str):
        body = self._url_to_body[url]

        class _Ctx:
            async def __aenter__(self):
                class _Resp:
                    status = 200

                    async def json(self):
                        return body

                    async def text(self):
                        return json.dumps(body)

                return _Resp()

            async def __aexit__(self, *args):
                return None

        return _Ctx()


async def test_downloader_publishes_request_and_returns_profile(
    fake_mqtt, capability_mwo_raw
) -> None:
    download_url = "https://capfiles.example.com/W11788386.json"
    session = _FakeSession({download_url: capability_mwo_raw})
    downloader = CapabilityDownloader(fake_mqtt, session)  # type: ignore[arg-type]

    said = "WPR1A00000001"
    model = "KMMC5019JBS"
    part = "W11788386"

    async def fire_response() -> None:
        # Give downloader time to subscribe + publish.
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        await fake_mqtt.inject(
            f"api/capability/download/{model}/{said}/response",
            {"url": download_url, "capabilityPartNumber": part},
        )

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
    download_url = "https://capfiles.example.com/W11788386.json"
    session = _FakeSession({download_url: capability_mwo_raw})
    downloader = CapabilityDownloader(fake_mqtt, session)  # type: ignore[arg-type]

    async def fire_response() -> None:
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        await fake_mqtt.inject(
            "api/capability/download/KMMC5019JBS/WPR1A00000001/response",
            {"url": download_url, "capabilityPartNumber": "W11788386"},
        )

    task = asyncio.create_task(
        downloader.get("WPR1A00000001", "KMMC5019JBS", "W11788386")
    )
    await fire_response()
    await task

    fake_mqtt.clear_published()

    # Second call should hit in-memory cache and NOT publish.
    profile = await downloader.get("WPR1A00000001", "KMMC5019JBS", "W11788386")
    assert profile.part_number == "W11788386"
    assert fake_mqtt.published == []


async def test_downloader_timeout_raises(fake_mqtt) -> None:
    session = _FakeSession({})
    downloader = CapabilityDownloader(
        fake_mqtt, session, timeout=0.05  # type: ignore[arg-type]
    )

    with pytest.raises(CapabilityDownloadError):
        await downloader.get("SAID", "MODEL", "PART")


async def test_downloader_disk_cache_hit(
    fake_mqtt, capability_mwo_raw, tmp_path: Path
) -> None:
    cache_dir = tmp_path / "caps"
    cache_dir.mkdir()
    (cache_dir / "W11788386.json").write_text(json.dumps(capability_mwo_raw))

    session = _FakeSession({})
    downloader = CapabilityDownloader(
        fake_mqtt, session, cache_dir=cache_dir  # type: ignore[arg-type]
    )

    profile = await downloader.get("SAID", "MODEL", "W11788386")
    assert profile.part_number == "W11788386"
    assert fake_mqtt.published == []
