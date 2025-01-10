import aioconsole

from whirlpool.washer import Washer


async def show_washer_menu(wr: Washer) -> None:
    def print_menu():
        print("\n")
        print(30 * "-", "MENU", 30 * "-")
        print("u. Update status from server")
        print("p. Print status")
        print("v. Print raw status")
        print("c. Custom command")
        print("q. Exit")
        print(67 * "-")

    def print_status(wr: Washer):
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

    wr.register_attr_callback(attr_upd)

    loop = True
    while loop:
        print_menu()
        choice = await aioconsole.ainput("Enter your choice: ")

        if choice == "p":
            print_status(wr)
        elif choice == "u":
            await wr.fetch_data()
            print_status(wr)
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

    wr.unregister_attr_callback(attr_upd)
