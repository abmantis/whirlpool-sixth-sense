"""Capture fixture data for a KitchenAid microwave.

Usage:
    python -m tools.capture_mwo_fixtures \
        --email you@example.com \
        --password 'password' \
        --brand KitchenAid \
        --region US \
        --said WPR1A00000001

Writes:
    tests/awsiot/data/thing_mwo.json
    tests/awsiot/data/capability_mwo.json
    tests/awsiot/data/state_mwo_full.json

The capability file is captured by reading the downloader's disk cache
after the first connect(), so this script also doubles as a smoke test
for the full discovery path.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

import aiohttp

from whirlpool.auth import Auth
from whirlpool.awsiot.appliancesmanager import AppliancesManager as AwsAppliancesManager
from whirlpool.backendselector import BackendSelector
from whirlpool.types import Brand, Region

LOGGER = logging.getLogger("capture_mwo_fixtures")

DATA_DIR = Path(__file__).resolve().parent.parent / "tests" / "awsiot" / "data"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument(
        "--brand", default="KitchenAid", choices=[b.name for b in Brand]
    )
    parser.add_argument("--region", default="US", choices=[r.name for r in Region])
    parser.add_argument(
        "--said",
        help="SAID of the microwave to capture (defaults to first discovered)",
    )
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


async def _amain(args: argparse.Namespace) -> int:
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    DATA_DIR.mkdir(parents=True, exist_ok=True)

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

        if not manager.microwaves:
            LOGGER.error("No microwave discovered")
            return 2

        mwo = manager.microwaves[0]
        if args.said and mwo.said != args.said:
            for m in manager.microwaves:
                if m.said == args.said:
                    mwo = m
                    break

        LOGGER.info("Capturing fixtures for %s (%s)", mwo.said, mwo.name)

        # Thing record: reconstruct what the manager saw.
        # (We only have ApplianceInfo here, so we write a reduced shape
        #  that satisfies the test fixtures.)
        thing_out = {
            "thingName": mwo.said,
            "thingTypeName": mwo.appliance_info.model_number,
            "attributes": {
                "Name": mwo.name.encode("utf-8").hex(),
                "Category": mwo.appliance_info.category.capitalize(),
                "Serial": mwo.appliance_info.serial_number,
                "CapabilityPartNumber": mwo.capability_profile.part_number,
            },
        }
        (DATA_DIR / "thing_mwo.json").write_text(
            json.dumps(thing_out, indent=2)
        )

        # Capability: dump the raw dict preserved on the profile.
        (DATA_DIR / "capability_mwo.json").write_text(
            json.dumps(mwo.capability_profile.raw, indent=2)
        )

        # State: dump the full accumulated state.
        (DATA_DIR / "state_mwo_full.json").write_text(
            json.dumps(mwo._state, indent=2)
        )

        LOGGER.info("Wrote fixtures to %s", DATA_DIR)

        await manager.disconnect()
    return 0


def main() -> None:
    args = _parse_args()
    sys.exit(asyncio.run(_amain(args)))


if __name__ == "__main__":
    main()
