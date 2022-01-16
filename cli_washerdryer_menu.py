import aioconsole

from whirlpool.washerdryer import WasherDryer, MachineState


async def show_washerdryer_menu(backend_selector, auth, said):
    def print_menu():
        print("\n")
        print(30 * "-", "MENU", 30 * "-")
        print("u. Update status from server")
        print("l. Load response from file")
        print("p. Print status")
        print("v. Print raw status")
        print("c. Custom command")
        print("q. Exit")
        print(67 * "-")

    def print_status(wd: WasherDryer):
        print("Online: " + str(wd.get_online()))
        print("State: " + str(wd.get_machine_state()))
        print("Pretty state: " + str(wd.get_machine_state_pretty()))
        print("Time Remaining (mins): " + str(wd.get_time_remaining_mins()))
        print("Total time remaining (delay + cycle): " + str(wd.get_total_delay_and_cycle_time_remaining_mins_pretty()))

        print("sensing: " + str(wd.get_cycle_status_sensing()))
        print("filling: " + str(wd.get_cycle_status_filling()))
        print("soaking: " + str(wd.get_cycle_status_soaking()))
        print("washing: " + str(wd.get_cycle_status_washing()))
        print("rinsing: " + str(wd.get_cycle_status_rinsing()))
        print("spinning: " + str(wd.get_cycle_status_spinning()))
        wd.get_cycle_status_pretty()
        print("Cylce status: " + str(wd.get_cycle_status_pretty()))

    def attr_upd():
        print("Attributes updated")

    wd = WasherDryer(backend_selector, auth, said, attr_upd)
    await wd.connect()

    loop = True
    while loop:
        print_menu()
        choice = await aioconsole.ainput("Enter your choice: ")

        if choice == "p":
            print_status(wd)
        elif choice == "u":
            await wd.fetch_data()
            print_status(wd)
        elif choice == "l":
            wd.load_from_file()
            print_status(wd)
        elif choice == "v":
            print(wd._data_dict)
        elif choice == "c":
            cmd = aioconsole.ainput("Command: ")
            val = aioconsole.ainput("Value: ")
            await wd.send_attributes({cmd: val})
        elif choice == "q":
            await wd.disconnect()
            auth.cancel_auto_renewal()
            print("Bye")
            loop = False
        else:
            print("Wrong option selection. Enter any key to try again..")
