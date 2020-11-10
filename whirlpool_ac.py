import aioconsole
import argparse
import asyncio
import logging

from whirlpool.aircon import Aircon, Mode, SETTING_REBOOT_WIFI, SETVAL_VALUE_ON
from whirlpool.auth import Auth

logging.basicConfig(format='%(asctime)s [%(name)s %(levelname)s]: %(message)s')
logger = logging.getLogger('whirlpool')
logger.setLevel(logging.DEBUG)

parser = argparse.ArgumentParser()
parser.add_argument('-e', '--email', help='Email address')
parser.add_argument('-p', '--password', help='Password')
args = parser.parse_args()


def print_menu():
    print('\n')
    print(30 * "-", "MENU", 30 * "-")
    print("1. Turn on")
    print("0. Turn off")
    print("+. Temp up")
    print("-. Temp down")
    print("C. Mode: Cool")
    print("H. Mode: Heat")
    print("F. Mode: Fan")
    print("S. Mode: Sixth Sense")
    print("2. Swing toggle")
    print("3. Turbo toggle")
    print("4. Eco toggle")
    print("5. Quiet toggle")
    print("6. Display toggle")
    print("u. Update status from server")
    print("p. Print status")
    print("v. Print raw status")
    print("r. Restart wifi")
    print("c. Custom command")
    print("q. Exit")
    print(67 * "-")


def print_status(ac: Aircon):
    print("online: " + str(ac.get_online()))
    print("power_on: " + str(ac.get_power_on()))
    print("temp: " + str(ac.get_temp()))
    print("humidity: " + str(ac.get_humidity()))
    print("current_temp: " + str(ac.get_current_temp()))
    print("current_humidity: " + str(ac.get_current_humidity()))
    print("mode: " + str(ac.get_mode()))
    print("sixthsense_mode: " + str(ac.get_sixthsense_mode()))
    print("fanspeed: " + str(ac.get_fanspeed()))
    print("h_louver_swing: " + str(ac.get_h_louver_swing()))
    print("turbo_mode: " + str(ac.get_turbo_mode()))
    print("eco_mode: " + str(ac.get_eco_mode()))
    print("quiet_mode: " + str(ac.get_quiet_mode()))
    print("display_on: " + str(ac.get_display_on()))


async def start():
    def attr_upd():
        logger.info("Attributes updated")

    auth = Auth(args.email, args.password)
    auth.load_auth_file()
    said = auth.get_said_list()[0]
    ac = Aircon(auth, said, attr_upd)
    await ac.connect()

    loop = True
    while(loop):
        print_menu()
        choice = await aioconsole.ainput("Enter your choice: ")

        if choice == '1':
            await ac.set_power_on(True)
        elif choice == '0':
            await ac.set_power_on(False)
        elif choice == '+':
            temp = ac.get_temp() + 1
            await ac.set_temp(temp)
        elif choice == '-':
            temp = ac.get_temp() - 1
            await ac.set_temp(temp)
        elif choice == 'C':
            await ac.set_mode(Mode.Cool)
        elif choice == 'H':
            await ac.set_mode(Mode.Heat)
        elif choice == 'F':
            await ac.set_mode(Mode.Fan)
        elif choice == 'S':
            await ac.set_mode(Mode.SixthSense)
        elif choice == '2':
            await ac.set_h_louver_swing(not ac.get_h_louver_swing())
        elif choice == '3':
            await ac.set_turbo_mode(not ac.get_turbo_mode())
        elif choice == '4':
            await ac.set_eco_mode(not ac.get_eco_mode())
        elif choice == '5':
            await ac.set_quiet_mode(not ac.get_quiet_mode())
        elif choice == '6':
            await ac.set_display_on(not ac.get_display_on())
        elif choice == 'p':
            print_status(ac)
        elif choice == 'u':
            await ac.fetch_data()
            print_status(ac)
        elif choice == 'v':
            print(ac._data_dict)
        elif choice == 'r':
            await ac.send_attributes({SETTING_REBOOT_WIFI: SETVAL_VALUE_ON})
        elif choice == 'c':
            cmd = aioconsole.ainput("Command: ")
            val = aioconsole.ainput("Value: ")
            await ac.send_attributes({cmd: val})
        elif choice == 'q':
            await ac.disconnect()
            print("Bye")
            loop = False
        else:
            print("Wrong option selection. Enter any key to try again..")

asyncio.get_event_loop().run_until_complete(start())
asyncio.get_event_loop().close()


# ISSUES:
# no recovery found yet (waiting X minutes?): { "message":"Appliance claimed successfully","status":"01" }
# rebooting wifi works: { "message":"Error in command execution or Invalid command","status":"03" }
