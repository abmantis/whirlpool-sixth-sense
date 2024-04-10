import aioconsole

from whirlpool.oven import Cavity, CookMode, KitchenTimerState, Oven


async def show_oven_menu(backend_selector, auth, said, session):
    def print_menu():
        print("\n")
        print(30 * "-", "MENU", 30 * "-")
        print("u. Update status from server")
        print("l. Control lock toggle")
        print("L. Light toggle")
        print("b. Set display brightness")
        print("t. Set cooking mode/temp")
        print("o. Stop/cancel cooking")
        print("k. Set kitchen timer")
        print("s. Toggle Sabbath mode")
        print("p. Print status")
        print("v. Print raw status")
        print("c. Custom command")
        print("q. Exit")
        print(67 * "-")

    def print_status(ov: Oven):
        print("online: " + str(ov.get_online()))
        print("display brightness (%): " + str(ov.get_display_brightness_percent()))
        print("control lock: " + str(ov.get_control_locked()))
        timer = ov.get_kitchen_timer(timer_id=1)
        timer_state = timer.get_state()
        print("kitchen timer 1 state: " + str(timer_state))
        if timer_state != KitchenTimerState.Standby:
            print(
                "kitchen timer 1 time remaining/set time: "
                + str(timer.get_remaining_time())
                + "/"
                + str(timer.get_total_time())
            )
        if ov.get_oven_cavity_exists(Cavity.Upper):
            print("upper meat probe: " + str(ov.get_meat_probe_status(Cavity.Upper)))
            print("upper light: " + str(ov.get_light(Cavity.Upper)))
            print("upper door open: " + str(ov.get_door_opened(Cavity.Upper)))
            print(
                "upper temp (current/target, in C): "
                + str(ov.get_temp(Cavity.Upper))
                + "/"
                + str(ov.get_target_temp(Cavity.Upper))
            )
            print("upper state: " + str(ov.get_cavity_state(Cavity.Upper)))
            print("upper cook mode: " + str(ov.get_cook_mode(Cavity.Upper)))
            print("upper cook time (seconds): " + str(ov.get_cook_time(Cavity.Upper)))
        if ov.get_oven_cavity_exists(Cavity.Lower):
            print("lower meat probe: " + str(ov.get_meat_probe_status(Cavity.Upper)))
            print("lower light: " + str(ov.get_light(Cavity.Lower)))
            print("lower door open: " + str(ov.get_door_opened(Cavity.Lower)))
            print(
                "lower temp (current/target, in C): "
                + str(ov.get_temp(Cavity.Lower))
                + "/"
                + str(ov.get_target_temp(Cavity.Lower))
            )
            print("lower state: " + str(ov.get_cavity_state(Cavity.Lower)))
            print("lower cook mode: " + str(ov.get_cook_mode(Cavity.Lower)))
            print("lower cook time (seconds): " + str(ov.get_cook_time(Cavity.Lower)))

    def attr_upd():
        print("Attributes updated")

    ov = Oven(backend_selector, auth, said, session)
    ov.register_attr_callback(attr_upd)
    await ov.connect()

    loop = True
    while loop:
        print_menu()
        choice = await aioconsole.ainput("Enter your choice: ")

        if choice == "p":
            print_status(ov)
        elif choice == "l":
            await ov.set_control_locked(not ov.get_control_locked())
        elif choice == "L":
            await ov.set_light(not ov.get_light())
        elif choice == "b":
            brightness = await aioconsole.ainput("Brightness (0-100): ")
            await ov.set_display_brightness_percent(brightness)
        elif choice == "k":
            minutes = await aioconsole.ainput("Timer minutes: ")
            await ov.get_kitchen_timer(timer_id=1).set_timer(int(float(minutes) * 60))
        elif choice == "o":
            await ov.stop_cook()
        elif choice == "t":
            print(
                """Cooking modes:
            b: Bake
            c: Convect Bake
            r: Broil
            o: Convect Broil
            s: Convect Roast
            a: Air Fry
            w: Keep Warm
            """
            )
            cookmode = await aioconsole.ainput("Enter cook mode: ")
            temp = await aioconsole.ainput("Enter cook temperature: ")
            if cookmode == "b":
                await ov.set_cook(mode=CookMode.Bake, target_temp=float(temp))
            if cookmode == "c":
                await ov.set_cook(mode=CookMode.ConvectBake, target_temp=float(temp))
            if cookmode == "r":
                await ov.set_cook(mode=CookMode.Broil, target_temp=float(temp))
            if cookmode == "o":
                await ov.set_cook(mode=CookMode.ConvectBroil, target_temp=float(temp))
            if cookmode == "s":
                await ov.set_cook(mode=CookMode.ConvectRoast, target_temp=float(temp))
            if cookmode == "a":
                await ov.set_cook(mode=CookMode.AirFry, target_temp=float(temp))
            if cookmode == "w":
                await ov.set_cook(mode=CookMode.KeepWarm, target_temp=float(temp))
            else:
                print("Invalid cook mode")
        elif choice == "s":
            await ov.set_sabbath_mode(not ov.get_sabbath_mode())
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
            print("Bye")
            loop = False
        else:
            print("Wrong option selection. Enter any key to try again..")
