"""Capture fixture data for any Whirlpool/KitchenAid/Maytag appliance.

NAME
    capture_fixtures - connect to the HTTP API and AWS IoT and dump appliance
    fixture data

SYNOPSIS
    python -m tools.capture_fixtures --email EMAIL --password PASSWORD
        [--brand BRAND] [--region REGION] (--said SAID | --all)
        [--output-dir DIR] [--no-redact] [--verbose]

    python -m tools.capture_fixtures --email EMAIL --password PASSWORD
        [--brand BRAND] [--region REGION] --list [--verbose]

OPTIONS
    --email EMAIL       Whirlpool account email (required)
    --password PASSWORD Whirlpool account password (prompted without echo if
                        omitted; explicit arguments may appear in process lists)
    --brand BRAND       One of: KitchenAid, Whirlpool, Maytag (required)
    --region REGION     One of: US, EU (required)
    --said SAID         SAID of a single appliance to capture
    --all               Capture fixtures for every discovered appliance
                        (one of --said or --all is required unless --list)
    --list              List all discovered appliances and exit
    --output-dir DIR    Base directory for output files
                        (default: tools/capture_fixtures_data/)
    --no-redact         Keep SAID, serial, wifi MAC, and user IDs in the
                        dumped JSON. By default they are scrubbed, and
                        SAID values are replaced with the same short hash
                        used in filenames so the fixtures remain
                        cross-referenceable.
    --verbose           Enable debug logging for all modules (by default
                        only this tool's own messages are logged). Library
                        logging requires --no-redact because it may contain
                        appliance identifiers and API payloads.

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

    # Capture one appliance's fixtures to the default capture dir:
    python -m tools.capture_fixtures \\
        --email you@example.com --password secret \\
        --said WPR1A00000001

    # Capture a Whirlpool EU dryer to a custom directory:
    python -m tools.capture_fixtures \\
        --email you@example.com --password secret \\
        --brand Whirlpool --region EU \\
        --said WPR2B00000002 --output-dir /tmp/fixtures

    # Capture with raw identifiers kept (not safe to share):
    python -m tools.capture_fixtures \\
        --email you@example.com --password secret \\
        --said WPR1A00000001 --no-redact

    # Capture every appliance on the account in one pass:
    python -m tools.capture_fixtures \\
        --email you@example.com --password secret \\
        --brand Maytag --all --output-dir /tmp/fixtures
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import hashlib
import json
import logging
import sys
import warnings
from pathlib import Path
from typing import Any

import aiohttp

from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.auth import Auth
from whirlpool.backendselector import BackendSelector
from whirlpool.httpapi.appliance import Appliance as HttpAppliance
from whirlpool.types import Brand, Region

LOGGER = logging.getLogger("capture_fixtures")

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "capture_fixtures_data"

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
        "Name",
        "sessionId",
    }
)


def _said_token(said: str) -> str:
    """Short pseudonymous identifier for a SAID (8 hex chars)."""
    return hashlib.sha256(said.encode("utf-8")).hexdigest()[:8]


def _fixture_suffix(model: str, said: str) -> str:
    """Build the '{model}-{hash}' suffix used in fixture filenames."""
    token = _said_token(said)
    return f"{model}-{token}" if model else token


def _redact(obj: Any, said: str) -> Any:
    """Recursively scrub known sensitive fields, not arbitrary unknown PII."""
    token = _said_token(said)

    def _scrub_sensitive(value: Any, replacement: str) -> Any:
        if isinstance(value, dict):
            return {
                k.replace(said, token) if said else k: v
                if k == "updateTime" and isinstance(v, int | float)
                else _scrub_sensitive(v, replacement)
                for k, v in value.items()
            }
        if isinstance(value, list):
            return [_scrub_sensitive(v, replacement) for v in value]
        return replacement

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
        return _scrub_sensitive(value, replacement)

    def _walk(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                k.replace(said, token) if said else k: _redact_key_value(k, v)
                for k, v in value.items()
            }
        if isinstance(value, list):
            return [_walk(v) for v in value]
        if isinstance(value, str) and said:
            return value.replace(said, token)
        return value

    return _walk(obj)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture HTTP API and AWS IoT fixture data for any appliance."
    )
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", help="Omit to enter the password without echo")
    parser.add_argument("--brand", choices=[b.name for b in Brand], required=True)
    parser.add_argument("--region", choices=[r.name for r in Region], required=True)
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
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Scrub SAID, serial, wifi MAC, and user IDs from dumped JSON",
    )
    args = parser.parse_args()
    if args.password is None:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", getpass.GetPassWarning)
                args.password = getpass.getpass("Whirlpool account password: ")
        except getpass.GetPassWarning, EOFError:
            parser.error("A terminal with hidden password input is required")
    if not args.password:
        parser.error("The password must not be empty")
    return args


async def _amain(args: argparse.Namespace) -> int:
    handler = logging.StreamHandler()
    if not args.verbose or args.redact:
        handler.addFilter(logging.Filter(LOGGER.name))
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[handler],
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
            identifier = _said_token(app.said) if args.redact else app.said
            name = "REDACTED" if args.redact else app.name
            print(f"  {identifier}  {_backend_name(app):<8} {tag:<15} {name}")
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
                _said_token(args.said) if args.redact else args.said,
            )
            return 4

    capture_failures = 0
    for appliance in targets:
        try:
            _capture_one(appliance, args.output_dir, redact=args.redact)
        except Exception:
            capture_failures += 1
            if args.redact:
                LOGGER.error(
                    "Failed to capture fixtures for %s", _said_token(appliance.said)
                )
            else:
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
        _said_token(appliance.said) if redact else appliance.said,
        "REDACTED" if redact else appliance.name,
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
        LOGGER.info("Wrote %s", path.name if redact else path)


def main() -> None:
    args = _parse_args()
    try:
        result = asyncio.run(_amain(args))
    except Exception:
        if not args.redact:
            raise
        LOGGER.error("Capture failed; details suppressed while redaction is enabled")
        result = 1
    sys.exit(result)


if __name__ == "__main__":
    main()
