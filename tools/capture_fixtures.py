"""Capture fixture data for any Whirlpool/KitchenAid/Maytag appliance.

NAME
    capture_fixtures - connect to the HTTP API and AWS IoT and dump appliance
    fixture data

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
    --output-dir DIR    Base directory for output files
                        (default: tests/data/)
    --redact            Scrub SAID, serial, wifi MAC, and user IDs from
                        the dumped JSON. SAID values are replaced with
                        the same short hash used in filenames so the
                        fixtures remain cross-referenceable.
    --verbose           Enable debug logging

OUTPUT FILES
    Each backend's files go in its own subdirectory of the output
    directory. Filenames embed the appliance type, the device model
    number, and a short hash of the SAID. This lets multiple appliances —
    even two of the same model — be captured into the same directory
    without overwriting each other, while keeping the filename safe to
    share (no raw SAID):

        httpapi/appliance_{type}_{model}-{hash}.json - appliance list record
        httpapi/data_{type}_{model}-{hash}.json      - appliance data
        awsiot/thing_{type}_{model}-{hash}.json      - IoT thing record
        awsiot/state_{type}_{model}-{hash}_full.json - full MQTT state snapshot

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

from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.auth import Auth
from whirlpool.backendselector import BackendSelector
from whirlpool.httpapi.appliance import Appliance as HttpAppliance
from whirlpool.types import Brand, Region

LOGGER = logging.getLogger("capture_fixtures")

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "tests" / "data"

_HTTPAPI = "httpapi"
_AWSIOT = "awsiot"

_TYPE_TAG: dict[str, str] = {
    "Aircon": "aircon",
    "Appliance": "unsupported",
    "Dryer": "dryer",
    "Oven": "oven",
    "Refrigerator": "refrigerator",
    "Washer": "washer",
}


def _appliance_tag(appliance: Any) -> str:
    """Derive a short tag from the appliance's class name."""
    cls_name = type(appliance).__name__
    return _TYPE_TAG.get(cls_name, cls_name.lower())


def _backend_name(appliance: Any) -> str:
    """Name of the backend the appliance was discovered through."""
    return _HTTPAPI if isinstance(appliance, HttpAppliance) else _AWSIOT


_SAID_KEYS = frozenset(
    {
        "thingName",
        "defaultClientId",
        "SAID",
        "said",
        "_id",
        "applianceId",
        "XCat_PersistentInfoSaid",
    }
)
_REDACTED_KEYS = frozenset(
    {
        "Serial",
        "serial",
        "SERIAL",
        "serialNumber",
        "serial_number",
        "SerialNumber",
        "XCat_ApplianceInfoSetSerialNumber",
        "WifiMacAddress",
        "wifi_mac",
        "wifiMacAddress",
        "MAC_Address",
        "XCat_PersistentInfoMacAddress",
        "UserId",
        "userId",
        "uid",
        "SmartID",
        "thingArn",
        "thingId",
        "APPLIANCE_NAME",
        "APPLIANCE_ID",
        "APPLIANCE_MASTER_ID",
        "DEVICE_ID",
        "LOCATION_ID",
        "Zip",
        "Generic_Zip",
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
        description="Capture HTTP API and AWS IoT fixture data for any appliance."
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
        help=f"Base directory for output files (default: {DEFAULT_OUTPUT_DIR})",
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

        manager = AppliancesManager(backend, auth, session)
        if not await manager.connect():
            LOGGER.error("Connect failed")
            return 1

        try:
            return _capture(args, manager)
        finally:
            await manager.disconnect()


def _capture(args: argparse.Namespace, manager: AppliancesManager) -> int:
    """List or capture the appliances discovered by the manager."""
    all_appliances = [
        *manager.aircons,
        *manager.dryers,
        *manager.washers,
        *manager.ovens,
        *manager.microwaves,
        *manager.refrigerators,
        *manager.unsupported_appliances,
    ]
    if not all_appliances:
        LOGGER.error("No appliances discovered")
        return 2

    if args.list_only:
        print(f"\nDiscovered {len(all_appliances)} appliance(s):\n")
        for app in all_appliances:
            tag = _appliance_tag(app)
            print(f"  {app.said}  {_backend_name(app):<8} {tag:<15} {app.name}")
        print()
        return 0

    if not args.capture_all and not args.said:
        LOGGER.error(
            "No --said or --all specified. Use --list to see available appliances."
        )
        return 3

    if args.capture_all:
        targets = all_appliances
    else:
        targets = [
            appliance for appliance in all_appliances if appliance.said == args.said
        ]
        if not targets:
            LOGGER.error(
                "SAID %s not found. Use --list to see available appliances.",
                args.said,
            )
            return 4

    capture_failures = 0
    for appliance in targets:
        try:
            _capture_one(appliance, args.output_dir, redact=args.redact)
        except Exception:
            capture_failures += 1
            LOGGER.exception("Failed to capture fixtures for %s", appliance.said)

    if capture_failures:
        LOGGER.error("Fixture capture failed for %d appliance(s)", capture_failures)
        return 5
    return 0


def _capture_one(appliance: Any, output_dir: Path, *, redact: bool) -> None:
    """Write the backend's fixture files for a single appliance."""
    backend_name = _backend_name(appliance)
    tag = _appliance_tag(appliance)
    LOGGER.info(
        "Capturing %s fixtures for %s (%s, type=%s)",
        backend_name,
        appliance.said,
        appliance.name,
        tag,
    )

    suffix = _fixture_suffix(appliance.appliance_info.model_number, appliance.said)
    raw_info = appliance.appliance_info.raw_info
    raw_data = appliance.get_raw_data() or {}
    if backend_name == _HTTPAPI:
        files = {
            f"appliance_{tag}_{suffix}.json": raw_info,
            f"data_{tag}_{suffix}.json": raw_data,
        }
    else:
        files = {
            f"thing_{tag}_{suffix}.json": raw_info,
            f"state_{tag}_{suffix}_full.json": raw_data,
        }

    backend_dir = output_dir / backend_name
    backend_dir.mkdir(parents=True, exist_ok=True)
    for filename, data in files.items():
        path = backend_dir / filename
        path.write_text(
            json.dumps(_redact(data, appliance.said) if redact else data, indent=2)
            + "\n",
            encoding="utf-8",
        )
        LOGGER.info("Wrote %s", path)


def main() -> None:
    args = _parse_args()
    sys.exit(asyncio.run(_amain(args)))


if __name__ == "__main__":
    main()
