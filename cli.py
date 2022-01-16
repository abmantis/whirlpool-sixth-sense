import aioconsole
import argparse
import asyncio
import logging
import math
from cli_ac_menu import show_aircon_menu
from cli_washerdryer_menu import show_washerdryer_menu

from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.backendselector import BackendSelector, Brand
from whirlpool.auth import Auth
from whirlpool.washerdryer import WasherDryer

logging.basicConfig(format="%(asctime)s [%(name)s %(levelname)s]: %(message)s")
logger = logging.getLogger("whirlpool")
logger.setLevel(logging.DEBUG)

logger = logging.getLogger("whirlpool.eventsocket")
logger.setLevel(logging.INFO)

parser = argparse.ArgumentParser()
parser.add_argument("-e", "--email", help="Email address")
parser.add_argument("-p", "--password", help="Password")
parser.add_argument(
    "-b", "--brand", help="Brand (whirlpool/maytag)", default="whirlpool"
)
parser.add_argument("-l", "--list", help="List appliances", action="store_true")
parser.add_argument("-s", "--said", help="The appliance to load")
args = parser.parse_args()


async def start():
    def attr_upd():
        logger.info("Attributes updated")

    if args.brand == "whirlpool":
        backend_selector = BackendSelector(Brand.Whirlpool)
    elif args.brand == "maytag":
        backend_selector = BackendSelector(Brand.Maytag)
    else:
        logger.error("Invalid brand argument")
        return

    auth = Auth(backend_selector, args.email, args.password)
    await auth.do_auth(store=False)
    appliance_manager = AppliancesManager(backend_selector, auth)
    if not await appliance_manager.fetch_appliances():
        logger.error("Could not fetch appliances")
        return

    if args.list:
        for index, cooler in enumerate(appliance_manager.aircons):
            print(index, cooler)
        for index, hole in enumerate(appliance_manager.washer_dryers):
            print(index, hole)
        applianceelementinput = input("Enter 0-" + str(index) + " for appliance details, otherwise type 'n': ")
        try:
            applianceelement = int(applianceelementinput)
        except ValueError:
            return
        print("Appliance selected: " + str(applianceelement))

        if hasattr(appliance_manager, "aircons"):
            if applianceelement < len(appliance_manager.aircons):
                args.said = appliance_manager.aircons[applianceelement]["SAID"]
                await show_aircon_menu(backend_selector, auth, args.said)
                return
        if hasattr(appliance_manager, "washer_dryers"):
            if applianceelement < len(appliance_manager.washer_dryers[applianceelement]["SAID"]):
                args.said = appliance_manager.washer_dryers[applianceelement]["SAID"]
                await show_washerdryer_menu(backend_selector, auth, args.said)
                return
        return

    if not args.said:
        logger.error("No appliance specified")
        return

    for ac_data in appliance_manager.aircons:
        if ac_data["SAID"] == args.said:
            await show_aircon_menu(backend_selector, auth, args.said)
            return

    for wd_data in appliance_manager.washer_dryers:
        if wd_data["SAID"] == args.said:
            await show_washerdryer_menu(backend_selector, auth, args.said)
            return


asyncio.run(start())
