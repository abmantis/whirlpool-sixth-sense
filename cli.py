import argparse
import asyncio
import json
import logging
from dataclasses import asdict

import aiohttp

from cli_ac_menu import show_aircon_menu
from cli_dryer_menu import show_dryer_menu
from cli_oven_menu import show_oven_menu
from cli_refrigerator_menu import show_refrigerator_menu
from cli_washer_menu import show_washer_menu
from whirlpool.appliance import Appliance
from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.auth import Auth
from whirlpool.backendselector import BackendSelector, Brand, Region

parser = argparse.ArgumentParser()
parser.add_argument("-e", "--email", help="Email address")
parser.add_argument("-p", "--password", help="Password")
parser.add_argument(
    "-b",
    "--brand",
    help="Brand (whirlpool/maytag/kitchenaid/consul)",
    default="whirlpool",
)
parser.add_argument("-r", "--region", help="Region (EU/US)", default="EU")
parser.add_argument("-l", "--list", help="List appliances", action="store_true")
parser.add_argument(
    "-d", "--dump", help="Dump appliance info and raw data", action="store_true"
)
parser.add_argument("-s", "--said", help="The appliance to load")
parser.add_argument(
    "-v", "--verbose", help="Enable verbose logging", action="store_true"
)
args = parser.parse_args()

if not args.email or not args.password:
    parser.print_help()
    raise SystemExit(1)

if args.verbose:
    logging.basicConfig(format="%(asctime)s [%(name)s %(levelname)s]: %(message)s")
    logging.getLogger("whirlpool").setLevel(logging.DEBUG)
    logging.getLogger("whirlpool.eventsocket").setLevel(logging.INFO)
else:
    logging.disable(logging.CRITICAL)

LOGGER = logging.getLogger(__name__)


async def start():
    if args.brand == "whirlpool":
        selected_brand = Brand.Whirlpool
    elif args.brand == "maytag":
        selected_brand = Brand.Maytag
    elif args.brand == "kitchenaid":
        selected_brand = Brand.KitchenAid
    elif args.brand == "consul":
        selected_brand = Brand.Consul
    else:
        LOGGER.error("Invalid brand argument")
        return

    if args.region == "EU":
        selected_region = Region.EU
    elif args.region == "US":
        selected_region = Region.US
    else:
        LOGGER.error("Invalid region argument")
        return

    backend_selector = BackendSelector(selected_brand, selected_region)

    class ConnectionManager:
        def __init__(self, manager: AppliancesManager) -> None:
            self._manager = manager

        async def __aenter__(self) -> None:
            await self._manager.connect()

        async def __aexit__(self, *args) -> None:
            await self._manager.disconnect()

    async with aiohttp.ClientSession() as session:
        auth = Auth(backend_selector, args.email, args.password, session)
        await auth.do_auth(store=False)
        appliance_manager = AppliancesManager(backend_selector, auth, session)

        async with ConnectionManager(appliance_manager):
            all_appliances: list[Appliance] = [
                *appliance_manager.aircons,
                *appliance_manager.dryers,
                *appliance_manager.washers,
                *appliance_manager.ovens,
                *appliance_manager.refrigerators,
            ]
            if args.list:
                print("\n".join(map(str, all_appliances)))
                return

            if args.dump:
                for appliance in all_appliances:
                    await appliance.fetch_data()
                    print(f"== {appliance} ==")
                    print("Appliance info:")
                    print(json.dumps(asdict(appliance.appliance_info), indent=2))
                    print("Raw data:")
                    print(json.dumps(appliance.get_raw_data(), indent=2))
                    print()
                return

            if not args.said:
                LOGGER.error("No appliance specified")
                return

            for ac_data in appliance_manager.aircons:
                if ac_data.said == args.said:
                    await show_aircon_menu(ac_data)
                    return

            for dr_data in appliance_manager.dryers:
                if dr_data.said == args.said:
                    await show_dryer_menu(dr_data)
                    return

            for wr_data in appliance_manager.washers:
                if wr_data.said == args.said:
                    await show_washer_menu(wr_data)
                    return

            for mo_data in appliance_manager.ovens:
                if mo_data.said == args.said:
                    await show_oven_menu(mo_data)
                    return

            for rf_data in appliance_manager.refrigerators:
                if rf_data.said == args.said:
                    await show_refrigerator_menu(rf_data)
                    return


asyncio.run(start())
