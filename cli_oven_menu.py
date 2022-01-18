import aioconsole
from whirlpool.oven import Oven, Cavity

async def show_oven_menu(backend_selector, auth, said):
    def print_menu():
        print("\n")
        print(30 * "-", "MENU", 30 * "-")
        print("u. Update status from server")
        print("l. Control lock toggle")
        print("p. Print status")
        print("v. Print raw status")
        print("c. Custom command")
        print("q. Exit")
        print(67 * "-")

    def print_status(ov: Oven):
        print("online: " + str(ov.get_online()))
        print("meat probe: " + str(ov.get_meat_probe_status()))
        print("display brightness (%): " + str(ov.get_display_brightness_percent()))
        print("control lock: " + str(ov.get_control_locked()))
        print("upper door open: " + str(ov.get_door_opened(Cavity.Upper)))
        print("lower door open: " + str(ov.get_door_opened(Cavity.Lower)))
        print("light: " + str(ov.get_light(Cavity.Upper)))

    def attr_upd():
        print("Attributes updated")

    ov = Oven(backend_selector, auth, said, attr_upd)
    await ov.connect()

    loop = True
    while loop:
        print_menu()
        choice = await aioconsole.ainput("Enter your choice: ")

        if choice == "p":
            print_status(ov)
        elif choice == "l":
            await ov.set_control_locked(not ov.get_control_locked())
        elif choice == "u":
            await ov.fetch_data()
            print_status(ov)
        elif choice == "v":
            print(ov._data_dict)
        elif choice == "c":
            cmd = aioconsole.ainput("Command: ")
            val = aioconsole.ainput("Value: ")
            await ov.send_attributes({cmd: val})
        elif choice == "q":
            await ov.disconnect()
            auth.cancel_auto_renewal()
            print("Bye")
            loop = False
        else:
            print("Wrong option selection. Enter any key to try again..")
