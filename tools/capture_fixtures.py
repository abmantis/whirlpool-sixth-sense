"""Capture fixture data for any Whirlpool/KitchenAid/Maytag AWS IoT appliance.

NAME
    capture_fixtures - connect to AWS IoT and dump appliance fixture data

SYNOPSIS
    python -m tools.capture_fixtures --email EMAIL --password PASSWORD
        [--brand BRAND] [--region REGION] --said SAID
        [--output-dir DIR] [--verbose]

    python -m tools.capture_fixtures --email EMAIL --password PASSWORD
        [--brand BRAND] [--region REGION] --list [--verbose]

OPTIONS
    --email EMAIL       Whirlpool account email (required)
    --password PASSWORD Whirlpool account password (required)
    --brand BRAND       One of: KitchenAid, Whirlpool, Maytag
                        (default: KitchenAid)
    --region REGION     One of: US, EU (default: US)
    --said SAID         SAID of the appliance to capture
                        (required unless --list)
    --list              List all discovered appliances and exit
    --output-dir DIR    Directory for output files
                        (default: tests/awsiot/data/)
    --verbose           Enable debug logging

OUTPUT FILES
    Filenames use the appliance type as prefix (e.g. "microwave",
    "dryer", "aircon", "oven", "refrigerator", "washer"):

        thing_{type}.json       - IoT thing record
        capability_{type}.json  - capability profile (raw XML-derived)
        state_{type}_full.json  - full MQTT state snapshot

EXAMPLES
    # List all appliances on a KitchenAid US account:
    python -m tools.capture_fixtures \\
        --email you@example.com --password secret --list

    # Capture microwave fixtures to the default test data dir:
    python -m tools.capture_fixtures \\
        --email you@example.com --password secret \\
        --said WPR1A00000001

    # Capture a Whirlpool EU dryer to a custom directory:
    python -m tools.capture_fixtures \\
        --email you@example.com --password secret \\
        --brand Whirlpool --region EU \\
        --said WPR2B00000002 --output-dir /tmp/fixtures

NOTES
    The capability file is read from the downloader's disk cache after
    connect(), so this script also doubles as a smoke test for the full
    AWS IoT discovery path.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

import aiohttp

from whirlpool_aws.auth import Auth
from whirlpool_aws.awsiot.appliancesmanager import AppliancesManager as AwsAppliancesManager
from whirlpool_aws.backendselector import BackendSelector
from whirlpool_aws.types import Brand, Region

LOGGER = logging.getLogger("capture_fixtures")

DEFAULT_OUTPUT_DIR = (
    Path(__file__).resolve().parent.parent / "tests" / "awsiot" / "data"
)

# Map class names to short fixture prefixes.
_TYPE_TAG: dict[str, str] = {
    "Aircon": "aircon",
    "Dryer": "dryer",
    "Microwave": "microwave",
    "Oven": "oven",
    "Refrigerator": "refrigerator",
    "Washer": "washer",
}


def _appliance_tag(appliance: Any) -> str:
    """Derive a short tag from the appliance's class name."""
    cls_name = type(appliance).__name__
    return _TYPE_TAG.get(cls_name, cls_name.lower())


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
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for output files (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument("--verbose", action="store_true")
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

        # --list mode: print all discovered appliances and exit.
        if args.list_only:
            print(f"\nDiscovered {len(all_appliances)} appliance(s):\n")
            for said, app in all_appliances.items():
                tag = _appliance_tag(app)
                print(f"  {said}  {tag:<15} {app.name}")
            print()
            await manager.disconnect()
            return 0

        # Capture mode: --said is required.
        if not args.said:
            LOGGER.error(
                "No --said specified. Use --list to see available appliances."
            )
            await manager.disconnect()
            return 3

        appliance = all_appliances.get(args.said)
        if appliance is None:
            LOGGER.error(
                "SAID %s not found. Use --list to see available appliances.",
                args.said,
            )
            await manager.disconnect()
            return 4

        tag = _appliance_tag(appliance)
        LOGGER.info(
            "Capturing fixtures for %s (%s, type=%s)",
            appliance.said, appliance.name, tag,
        )

        # Access awsiot internals for fixture capture.
        impl: Any = appliance

        output_dir: Path = args.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        # Thing record.
        thing_out = {
            "thingName": appliance.said,
            "thingTypeName": appliance.appliance_info.model_number,
            "attributes": {
                "Name": appliance.name.encode("utf-8").hex(),
                "Category": appliance.appliance_info.category.capitalize(),
                "Serial": appliance.appliance_info.serial_number,
                "CapabilityPartNumber": impl.capability_profile.part_number,
            },
        }
        thing_path = output_dir / f"thing_{tag}.json"
        thing_path.write_text(json.dumps(thing_out, indent=2))
        LOGGER.info("Wrote %s", thing_path)

        # Capability profile.
        cap_path = output_dir / f"capability_{tag}.json"
        cap_path.write_text(json.dumps(impl.capability_profile.raw, indent=2))
        LOGGER.info("Wrote %s", cap_path)

        # Full state snapshot.
        state_path = output_dir / f"state_{tag}_full.json"
        state_path.write_text(json.dumps(impl._state, indent=2))
        LOGGER.info("Wrote %s", state_path)

        await manager.disconnect()
    return 0


def main() -> None:
    args = _parse_args()
    sys.exit(asyncio.run(_amain(args)))


if __name__ == "__main__":
    main()
