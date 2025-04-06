import argparse
import asyncio
import logging

import aiohttp

from cli_ac_menu import show_aircon_menu
from cli_dryer_menu import show_dryer_menu
from cli_oven_menu import show_oven_menu
from cli_refrigerator_menu import show_refrigerator_menu
from cli_washer_menu import show_washer_menu
from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.auth import Auth
from whirlpool.backendselector import BackendSelector, Brand, Region

logging.basicConfig(format="%(asctime)s [%(name)s %(levelname)s]: %(message)s")
logger = logging.getLogger("whirlpool")
logger.setLevel(logging.DEBUG)

logger = logging.getLogger("whirlpool.eventsocket")
logger.setLevel(logging.INFO)

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
parser.add_argument("-s", "--said", help="The appliance to load")
args = parser.parse_args()


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
        logger.error("Invalid brand argument")
        return

    if args.region == "EU":
        selected_region = Region.EU
    elif args.region == "US":
        selected_region = Region.US
    else:
        logger.error("Invalid region argument")
        return

    backend_selector = BackendSelector(selected_brand, selected_region)

    async with aiohttp.ClientSession() as session:
        auth = Auth(backend_selector, args.email, args.password, session)
        await auth.do_auth(store=False)
        appliance_manager = AppliancesManager(backend_selector, auth, session)
        if not await appliance_manager.fetch_appliances():
            logger.error("Could not fetch appliances")
            return

        if args.list:
            if appliance_manager.aircons:
                print("\n".join(map(str, appliance_manager.aircons)))

            if appliance_manager.washer_dryers:
                print("\n".join(map(str, appliance_manager.washer_dryers)))

            if appliance_manager.ovens:
                print("\n".join(map(str, appliance_manager.ovens)))

            if appliance_manager.refrigerators:
                print("\n".join(map(str, appliance_manager.refrigerators)))
            return

        if not args.said:
            logger.error("No appliance specified")
            return

        class Connection:
            def __init__(self, manager: AppliancesManager) -> None:
                self._manager = manager

            async def __aenter__(self) -> None:
                await self._manager.connect()

            async def __aexit__(self, *args) -> None:
                await self._manager.disconnect()

        async with Connection(appliance_manager):
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
