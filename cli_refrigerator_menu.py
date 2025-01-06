import aioconsole

from whirlpool.refrigerator import Refrigerator


async def show_refrigerator_menu(backend_selector, auth, said, session):
    def print_menu():
        print("\n")
        print(30 * "-", "MENU", 30 * "-")
        print("+. Temp up")
        print("-. Temp down")
        print("-4. Set -4°C")
        print("-2. Set -2°C")
        print("0. Set 0°C")
        print("3. Set 3°C")
        print("5. Set 5°C")
        print("t. Turbo toggle")
        print("l. Display lock toggle")
        print("u. Update status from server")
        print("p. Print status")
        print("r. Print raw status")
        print("c. Custom command")
        print("q. Exit")
        print(67 * "-")

    def print_status(bc: Refrigerator):
        print("current_temp: " + str(rf.get_offset_temp(True)) + "°C")
        print("turbo_mode: " + str(rf.get_turbo_mode()))
        print("display_locked: " + str(rf.get_display_lock()))

    def attr_upd():
        print("Attributes updated")

    rf = Refrigerator(backend_selector, auth, said, session)
    rf.register_attr_callback(attr_upd)
    await rf.connect()

    loop = True
    while loop:
        print_menu()
        choice = await aioconsole.ainput("Enter your choice: ")

        if choice == "+":
            temp = rf.get_temp() - 1
            await rf.set_temp(temp)
        elif choice == "-":
            temp = rf.get_temp() + 1
            await rf.set_temp(temp)
        elif choice in ["-4", "-2", "0", "3", "5"]:
            temp = int(choice)
            await rf.set_offset_temp(temp)
        elif choice == "t":
            await rf.set_turbo_mode(not rf.get_turbo_mode())
        elif choice == "l":
            await rf.set_display_lock(not rf.get_display_lock())
        elif choice == "p":
            print_status(rf)
        elif choice == "u":
            await rf.fetch_data()
            print_status(rf)
        elif choice == "r":
            print(rf._data_dict)
        elif choice == "c":
            cmd = await aioconsole.ainput("Command: ")
            val = await aioconsole.ainput("Value: ")
            await rf.send_attributes({cmd: val})
        elif choice == "q":
            await rf.disconnect()
            print("Bye")
            loop = False
        else:
            print("Wrong option selection. Enter any key to try again..")
