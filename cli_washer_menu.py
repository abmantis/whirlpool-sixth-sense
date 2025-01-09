import aioconsole
import aiohttp

from whirlpool.appliancesmanager import AppliancesManager
from whirlpool.auth import Auth
from whirlpool.backendselector import BackendSelector
from whirlpool.washer import Washer
from whirlpool.types import ApplianceData

async def show_washer_menu(
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

    def print_status(wd: Washer):
        print("online: " + str(wr.get_online()))
        print("state: " + str(wr.get_machine_state()))
        print("sensing: " + str(wr.get_cycle_status_sensing()))
        print("filling: " + str(wr.get_cycle_status_filling()))
        print("soaking: " + str(wr.get_cycle_status_soaking()))
        print("washing: " + str(wr.get_cycle_status_washing()))
        print("rinsing: " + str(wr.get_cycle_status_rinsing()))
        print("spinning: " + str(wr.get_cycle_status_spinning()))

    def attr_upd():
        print("Attributes updated")

    wd = Washer(backend_selector, auth, session, app_data)
    wr.register_attr_callback(attr_upd)
    await manager.connect()

    loop = True
    while loop:
        print_menu()
        choice = await aioconsole.ainput("Enter your choice: ")

        if choice == "p":
            print_status(wd)
        elif choice == "u":
            await wr.fetch_data()
            print_status(wd)
        elif choice == "v":
            print(wr._data_dict)
        elif choice == "c":
            cmd = await aioconsole.ainput("Command: ")
            val = await aioconsole.ainput("Value: ")
            await wr.send_attributes({cmd: val})
        elif choice == "q":
            print("Bye")
            loop = False
        else:
            print("Wrong option selection. Enter any key to try again..")

    await manager.disconnect()
