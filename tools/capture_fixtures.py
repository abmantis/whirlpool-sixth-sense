"""Capture fixture data for any Whirlpool/KitchenAid/Maytag AWS IoT appliance.

NAME
    capture_fixtures - connect to AWS IoT and dump appliance fixture data

SYNOPSIS
    python -m tools.capture_fixtures --email EMAIL --password PASSWORD
        [--brand BRAND] [--region REGION] (--said SAID | --all)
        [--output-dir DIR] [--redact] [--verbose]

    python -m tools.capture_fixtures --email EMAIL --password PASSWORD
        [--brand BRAND] [--region REGION] --list [--verbose]

OPTIONS
    --email EMAIL       Whirlpool account email (required)
    --password PASSWORD Whirlpool account password (required)
    --brand BRAND       One of: KitchenAid, Whirlpool, Maytag
                        (default: KitchenAid)
    --region REGION     One of: US, EU (default: US)
    --said SAID         SAID of a single appliance to capture
    --all               Capture fixtures for every discovered appliance
                        (one of --said or --all is required unless --list)
    --list              List all discovered appliances and exit
    --output-dir DIR    Directory for output files
                        (default: tests/awsiot/data/)
    --redact            Scrub SAID, serial, wifi MAC, and user IDs from
                        the dumped JSON. SAID values are replaced with
                        the same short hash used in filenames so the
                        fixtures remain cross-referenceable.
    --verbose           Enable debug logging

OUTPUT FILES
    Filenames embed the appliance type, the device model number, and a
    short hash of the SAID. This lets multiple appliances — even two of
    the same model — be captured into the same directory without
    overwriting each other, while keeping the filename safe to share
    (no raw SAID):

        thing_{type}_{model}-{hash}.json       - IoT thing record
        state_{type}_{model}-{hash}_full.json  - full MQTT state snapshot

    If the model number is unavailable, only the hash is used.

EXAMPLES
    # List all appliances on a KitchenAid US account:
    python -m tools.capture_fixtures \\
        --email you@example.com --password secret --list

    # Capture one appliance's fixtures to the default test data dir:
    python -m tools.capture_fixtures \\
        --email you@example.com --password secret \\
        --said WPR1A00000001

    # Capture a Whirlpool EU dryer to a custom directory:
    python -m tools.capture_fixtures \\
        --email you@example.com --password secret \\
        --brand Whirlpool --region EU \\
        --said WPR2B00000002 --output-dir /tmp/fixtures

    # Capture with sensitive identifiers scrubbed, safe to share:
    python -m tools.capture_fixtures \\
        --email you@example.com --password secret \\
        --said WPR1A00000001 --redact

    # Capture every appliance on the account in one pass:
    python -m tools.capture_fixtures \\
        --email you@example.com --password secret \\
        --brand Maytag --all --redact --output-dir /tmp/fixtures
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import sys
from pathlib import Path
from typing import Any

import aiohttp

from whirlpool.auth import Auth
from whirlpool.awsiot.appliancesmanager import (
    AppliancesManager as AwsAppliancesManager,
)
from whirlpool.backendselector import BackendSelector
from whirlpool.types import Brand, Region

LOGGER = logging.getLogger("capture_fixtures")

DEFAULT_OUTPUT_DIR = (
    Path(__file__).resolve().parent.parent / "tests" / "awsiot" / "data"
)

_TYPE_TAG: dict[str, str] = {
    "Aircon": "aircon",
    "Dryer": "dryer",
    "Oven": "oven",
    "Refrigerator": "refrigerator",
    "Washer": "washer",
}
_THING_CATEGORY_TAG: dict[str, str] = {
    "airconditioner": "AirConditioner",
    "cooking": "Cooking",
    "fabriccare": "FabricCare",
    "laundry": "Laundry",
    "refrigerator": "Refrigerator",
}


def _appliance_tag(appliance: Any) -> str:
    """Derive a short tag from the appliance's class name."""
    cls_name = type(appliance).__name__
    return _TYPE_TAG.get(cls_name, cls_name.lower())


def _thing_category(category: str) -> str:
    """Map internal lowercase categories back to AWS thing metadata values."""
    return _THING_CATEGORY_TAG.get(category, category)


_SAID_KEYS = frozenset({"thingName", "SAID", "said"})
_REDACTED_KEYS = frozenset(
    {
        "Serial",
        "serial",
        "serialNumber",
        "serial_number",
        "WifiMacAddress",
        "wifi_mac",
        "wifiMacAddress",
        "UserId",
        "userId",
    }
)


def _said_token(said: str) -> str:
    """Short, non-reversible identifier for a SAID (8 hex chars)."""
    return hashlib.sha256(said.encode("utf-8")).hexdigest()[:8]


def _fixture_suffix(model: str, said: str) -> str:
    """Build the '{model}-{hash}' suffix used in fixture filenames."""
    token = _said_token(said)
    return f"{model}-{token}" if model else token


def _redact(obj: Any, said: str) -> Any:
    """Recursively scrub sensitive keys from a JSON-like structure."""
    token = _said_token(said)

    def _redact_key_value(key: str, value: Any) -> Any:
        replacement = (
            token
            if key in _SAID_KEYS
            else "REDACTED"
            if key in _REDACTED_KEYS
            else None
        )
        if replacement is None:
            return _walk(value)
        if isinstance(value, dict):
            return {
                k: replacement if k == "value" else _walk(v) for k, v in value.items()
            }
        if isinstance(value, list):
            return [
                _walk(v) if isinstance(v, dict | list) else replacement for v in value
            ]
        return replacement

    def _walk(value: Any) -> Any:
        if isinstance(value, dict):
            return {k: _redact_key_value(k, v) for k, v in value.items()}
        if isinstance(value, list):
            return [_walk(v) for v in value]
        return value

    return _walk(obj)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture AWS IoT fixture data for any appliance."
    )
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument(
        "--brand", default="KitchenAid", choices=[b.name for b in Brand]
    )
    parser.add_argument("--region", default="US", choices=[r.name for r in Region])
    parser.add_argument(
        "--said",
        help="SAID of the appliance to capture (required unless --list)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_only",
        help="List all discovered appliances and exit",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="capture_all",
        help="Capture fixtures for every discovered appliance",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for output files (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--redact",
        action="store_true",
        help="Scrub SAID, serial, wifi MAC, and user IDs from dumped JSON",
    )
    return parser.parse_args()


async def _amain(args: argparse.Namespace) -> int:
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    brand = Brand[args.brand]
    region = Region[args.region]
    backend = BackendSelector(brand, region)

    async with aiohttp.ClientSession() as session:
        auth = Auth(backend, args.email, args.password, session)
        await auth.do_auth()

        manager = AwsAppliancesManager(auth, session, lambda: None)
        ok = await manager.connect()
        if not ok:
            LOGGER.error("AWS IoT connect failed")
            return 1

        all_appliances = manager.all_appliances
        if not all_appliances:
            LOGGER.error("No appliances discovered")
            await manager.disconnect()
            return 2

        if args.list_only:
            print(f"\nDiscovered {len(all_appliances)} appliance(s):\n")
            for said, app in all_appliances.items():
                tag = _appliance_tag(app)
                print(f"  {said}  {tag:<15} {app.name}")
            print()
            await manager.disconnect()
            return 0

        if not args.capture_all and not args.said:
            LOGGER.error(
                "No --said or --all specified. Use --list to see available appliances."
            )
            await manager.disconnect()
            return 3

        output_dir: Path = args.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        if args.capture_all:
            targets = list(all_appliances.values())
        else:
            appliance = all_appliances.get(args.said)
            if appliance is None:
                LOGGER.error(
                    "SAID %s not found. Use --list to see available appliances.",
                    args.said,
                )
                await manager.disconnect()
                return 4
            targets = [appliance]

        capture_failures = 0
        for appliance in targets:
            try:
                _capture_one(appliance, output_dir, redact=args.redact)
            except Exception:
                capture_failures += 1
                LOGGER.exception("Failed to capture fixtures for %s", appliance.said)

        if capture_failures:
            LOGGER.error("Fixture capture failed for %d appliance(s)", capture_failures)

        await manager.disconnect()
    return 5 if capture_failures else 0


def _capture_one(appliance: Any, output_dir: Path, *, redact: bool) -> None:
    """Write thing/state fixture files for a single appliance."""
    tag = _appliance_tag(appliance)
    LOGGER.info(
        "Capturing fixtures for %s (%s, type=%s)",
        appliance.said,
        appliance.name,
        tag,
    )

    thing_out = {
        "thingName": appliance.said,
        "thingTypeName": appliance.appliance_info.model_number,
        "attributes": {
            "Name": appliance.name.encode("utf-8").hex(),
            "Category": _thing_category(appliance.appliance_info.category),
            "Serial": appliance.appliance_info.serial_number,
        },
    }
    suffix = _fixture_suffix(appliance.appliance_info.model_number, appliance.said)

    def _maybe_redact(data: Any) -> Any:
        return _redact(data, appliance.said) if redact else data

    thing_path = output_dir / f"thing_{tag}_{suffix}.json"
    thing_path.write_text(
        json.dumps(_maybe_redact(thing_out), indent=2) + "\n",
        encoding="utf-8",
    )
    LOGGER.info("Wrote %s", thing_path)

    state_path = output_dir / f"state_{tag}_{suffix}_full.json"
    state_path.write_text(
        json.dumps(_maybe_redact(appliance.get_raw_data() or {}), indent=2) + "\n",
        encoding="utf-8",
    )
    LOGGER.info("Wrote %s", state_path)


def main() -> None:
    args = _parse_args()
    sys.exit(asyncio.run(_amain(args)))


if __name__ == "__main__":
    main()
