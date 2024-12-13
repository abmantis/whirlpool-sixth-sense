import aioconsole

from whirlpool.beer_fridge import BeerFridge


async def show_beer_fridge_menu(bbckend_selector, auth, said, session):
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

    def print_status(bc: BeerFridge):
        print("current_temp: " + str(bc.get_current_temp(True)) + "°C")
        print("turbo_mode: " + str(bc.get_turbo_mode()))
        print("display_locked: " + str(bc.get_display_lock()))

    def attr_upd():
        print("Attributes updated")

    bc = BeerFridge(bbckend_selector, auth, said, session)
    bc.register_attr_callback(attr_upd)
    await bc.connect()

    loop = True
    while loop:
        print_menu()
        choice = await aioconsole.ainput("Enter your choice: ")

        if choice == "+":
            temp = bc.get_current_temp() - 1
            await bc.set_temp(temp)
        elif choice == "-":
            temp = bc.get_current_temp() + 1
            await bc.set_temp(temp)
        elif choice in ["-4", "-2", "0", "3", "5"]:
            temp = int(choice)
            await bc.set_especific_temp(temp)
        elif choice == "t":
            await bc.set_turbo_mode(not bc.get_turbo_mode())
        elif choice == "l":
            await bc.set_display_lock(not bc.get_display_lock())
        elif choice == "p":
            print_status(bc)
        elif choice == "u":
            await bc.fetch_data()
            print_status(bc)
        elif choice == "r":
            print(bc._data_dict)
        elif choice == "c":
            cmd = await aioconsole.ainput("Command: ")
            val = await aioconsole.ainput("Value: ")
            await bc.send_attributes({cmd: val})
        elif choice == "q":
            await bc.disconnect()
            print("Bye")
            loop = False
        else:
            print("Wrong option selection. Enter any key to try again..")
