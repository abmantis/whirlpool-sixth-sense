import aioconsole
import argparse
import asyncio
import logging

from whirlpool.cooktop import Cookop, SETTING_REBOOT_WIFI
from whirlpool.auth import Auth

logging.basicConfig(format="%(asctime)s [%(name)s %(levelname)s]: %(message)s")
logger = logging.getLogger("whirlpool")
logger.setLevel(logging.INFO)

parser = argparse.ArgumentParser()
parser.add_argument("-e", "--email", help="Email address")
parser.add_argument("-p", "--password", help="Password")
args = parser.parse_args()


def print_menu():
    print("\n")
    print(30 * "-", "MENU", 30 * "-")
    print("u. Update status from server")
    print("p. Print status")
    print("v. Print raw status")
    print("c. Custom command")
    print("q. Exit")
    print(67 * "-")


def print_status(ct: Cookop):
    print("online: " + str(ct.get_online()))
    print("state: " + str(ct.get_state()))
    print("element_state: " + str(ct.get_element_state()))
    print("element_time_elapsed: " + str(ct.get_element_time_elapsed()))
    print("element_time_remaining: " + str(ct.get_element_time_remaining()))
    print("element_percent_complete: " + str(ct.get_element_percent_complete()))
    print("element_notification: " + str(ct.get_element_notification()))


async def start():
    def attr_upd():
        logger.info("Attributes updated")

    auth = Auth(args.email, args.password)
    await auth.load_auth_file()
    said = auth.get_said_list()[0]
    ct = Cookop(auth, said, attr_upd)
    await ct.connect()

    loop = True
    while loop:
        print_menu()
        choice = await aioconsole.ainput("Enter your choice: ")

        if choice == "p":
            print_status(ct)
        elif choice == "u":
            await ct.fetch_data()
            print_status(ct)
        elif choice == "v":
            print(ct._data_dict)
        elif choice == "c":
            cmd = aioconsole.ainput("Command: ")
            val = aioconsole.ainput("Value: ")
            await ct.send_attributes({cmd: val})
        elif choice == "q":
            await ct.disconnect()
            auth.cancel_auto_renewal()
            print("Bye")
            loop = False
        else:
            print("Wrong option selection. Enter any key to try again..")


asyncio.get_event_loop().run_until_complete(start())
asyncio.get_event_loop().close()
