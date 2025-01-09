import aioconsole
import aiohttp

from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.auth import Auth
from whirlpool.backendselector import BackendSelector
from whirlpool.washerdryer import WasherDryer
from whirlpool.types import ApplianceData

async def show_washerdryer_menu(
    manager: AppliancesManager,
    backend_selector: BackendSelector,
    auth: Auth,
    session: aiohttp.ClientSession,
    app_data: ApplianceData
) -> None:
    def print_menu():
        print("\n")
        print(30 * "-", "MENU", 30 * "-")
        print("u. Update status from server")
        print("p. Print status")
        print("v. Print raw status")
        print("c. Custom command")
        print("q. Exit")
        print(67 * "-")

    def print_status(wd: WasherDryer):
        print("online: " + str(wd.get_online()))
        print("state: " + str(wd.get_machine_state()))
        print("sensing: " + str(wd.get_cycle_status_sensing()))
        print("filling: " + str(wd.get_cycle_status_filling()))
        print("soaking: " + str(wd.get_cycle_status_soaking()))
        print("washing: " + str(wd.get_cycle_status_washing()))
        print("rinsing: " + str(wd.get_cycle_status_rinsing()))
        print("spinning: " + str(wd.get_cycle_status_spinning()))

    def attr_upd():
        print("Attributes updated")

    wd = WasherDryer(backend_selector, auth, session, app_data)
    wd.register_attr_callback(attr_upd)
    await manager.connect()

    loop = True
    while loop:
        print_menu()
        choice = await aioconsole.ainput("Enter your choice: ")

        if choice == "p":
            print_status(wd)
        elif choice == "u":
            await wd.fetch_data()
            print_status(wd)
        elif choice == "v":
            print(wd._data_dict)
        elif choice == "c":
            cmd = await aioconsole.ainput("Command: ")
            val = await aioconsole.ainput("Value: ")
            await wd.send_attributes({cmd: val})
        elif choice == "q":
            print("Bye")
            loop = False
        else:
            print("Wrong option selection. Enter any key to try again..")

    await manager.disconnect()
