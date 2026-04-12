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
