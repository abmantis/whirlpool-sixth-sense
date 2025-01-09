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
from whirlpool.backendselector import BackendSelector
from whirlpool.types import ApplianceKind, Brand, Region

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
            print(appliance_manager.aircons)
            print(appliance_manager.dryer)
            print(appliance_manager.ovens)
            print(appliance_manager.refrigerators)
            print(appliance_manager.washers)
            return

        if not args.said:
            logger.error("No appliance specified")
            return

        app = appliance_manager.get_appliance(args.said)
        if not app:
            logger.error(f"{said} wasn't found");
            return

        await appliance_manager.connect()

        match app.Kind:
            case ApplianceKind.AirCon:
                await show_aircon_menu(app)
            case ApplianceKind.Dryer:
                await show_dryer_menu(app)
            case ApplianceKind.Oven:
                await show_oven_menu(app)
            case ApplianceKind.Refrigerator:
                await show_refrigerator_menu(app)
            case ApplianceKind.Washer:
                await show_washer_menu(app)

        await manager.disconnect()

asyncio.run(start())
