import argparse
import asyncio
import logging

import aiohttp

from cli_ac_menu import show_aircon_menu
from cli_oven_menu import show_oven_menu
from cli_washerdryer_menu import show_washerdryer_menu
from cli_beer_fridge_menu import show_beer_fridge_menu
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
    "-b", "--brand", help="Brand (whirlpool/maytag/kitchenaid/consul)", default="whirlpool"
)
parser.add_argument("-r", "--region", help="Region (EU/US)", default="EU")
parser.add_argument("-l", "--list", help="List appliances", action="store_true")
parser.add_argument("-s", "--said", help="The appliance to load")
args = parser.parse_args()


async def start():
    def attr_upd():
        logger.info("Attributes updated")

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
            print(appliance_manager.washer_dryers)
            print(appliance_manager.ovens)
            print(appliance_manager.beer_fridges)
            # return

        for ac_data in appliance_manager.aircons:
            if ac_data["SAID"] == args.said:
                await show_aircon_menu(backend_selector, auth, args.said, session)
                return

        for wd_data in appliance_manager.washer_dryers:
            if wd_data["SAID"] == args.said:
                await show_washerdryer_menu(backend_selector, auth, args.said, session)
                return

        for mo_data in appliance_manager.ovens:
            if mo_data["SAID"] == args.said:
                await show_oven_menu(backend_selector, auth, args.said, session)
                return
        
        for bf_data in appliance_manager.beer_fridges:
            if bf_data["SAID"]:
                await show_beer_fridge_menu(backend_selector, auth, bf_data["SAID"], session)
                return
            
        if not args.said:
            logger.error("No appliance specified")
            return


asyncio.run(start())
