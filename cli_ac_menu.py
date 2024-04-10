import aioconsole

from whirlpool.aircon import Aircon, Mode


async def show_aircon_menu(backend_selector, auth, said, session):
    def print_menu():
        print("\n")
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

    def attr_upd():
        print("Attributes updated")

    ac = Aircon(backend_selector, auth, said, session)
    ac.register_attr_callback(attr_upd)
    await ac.connect()

    loop = True
    while loop:
        print_menu()
        choice = await aioconsole.ainput("Enter your choice: ")

        if choice == "1":
            await ac.set_power_on(True)
        elif choice == "0":
            await ac.set_power_on(False)
        elif choice == "+":
            temp = ac.get_temp() + 1
            await ac.set_temp(temp)
        elif choice == "-":
            temp = ac.get_temp() - 1
            await ac.set_temp(temp)
        elif choice == "C":
            await ac.set_mode(Mode.Cool)
        elif choice == "H":
            await ac.set_mode(Mode.Heat)
        elif choice == "F":
            await ac.set_mode(Mode.Fan)
        elif choice == "S":
            await ac.set_mode(Mode.SixthSense)
        elif choice == "2":
            await ac.set_h_louver_swing(not ac.get_h_louver_swing())
        elif choice == "3":
            await ac.set_turbo_mode(not ac.get_turbo_mode())
        elif choice == "4":
            await ac.set_eco_mode(not ac.get_eco_mode())
        elif choice == "5":
            await ac.set_quiet_mode(not ac.get_quiet_mode())
        elif choice == "6":
            await ac.set_display_on(not ac.get_display_on())
        elif choice == "p":
            print_status(ac)
        elif choice == "u":
            await ac.fetch_data()
            print_status(ac)
        elif choice == "v":
            print(ac._data_dict)
        elif choice == "c":
            cmd = aioconsole.ainput("Command: ")
            val = aioconsole.ainput("Value: ")
            await ac.send_attributes({cmd: val})
        elif choice == "q":
            await ac.disconnect()
            print("Bye")
            loop = False
        else:
            print("Wrong option selection. Enter any key to try again..")
