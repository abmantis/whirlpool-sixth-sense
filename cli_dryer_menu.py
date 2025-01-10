import aioconsole

from whirlpool.dryer import Dryer


async def show_dryer_menu(dr: Dryer) -> None:
    def print_menu() -> None:
        print("\n")
        print(30 * "-", "MENU", 30 * "-")
        print("u. Update status from server")
        print("p. Print status")
        print("v. Print raw status")
        print("c. Custom command")
        print("q. Exit")
        print(67 * "-")

    def print_status(dr: Dryer) -> None:
        print(f"online: {dr.get_online()}")
        print(f"state: {dr.get_machine_state_value()}")
        print(f"door open: {dr.get_op_status_dooropen()}")
        print(f"est time remaining: {dr.get_time_status_est_time_remaining()}")
        print(f"extra power changeable: {dr.get_change_status_extrapowerchangeable()}")
        print(f"steam changeable: {dr.get_change_status_steamchangeable()}")
        print(f"cycle select: {dr.get_change_status_cycleselect()}")
        print(f"dryness: {dr.get_change_status_dryness()}")
        print(f"manual dry time: {dr.get_change_status_manualdrytime()}")
        print(f"static guard: {dr.get_change_status_staticguard()}")
        print(f"temperature: {dr.get_change_status_temperature()}")
        print(f"wrinkle shield: {dr.get_change_status_wrinkleshield()}")
        print(f"airflow status: {dr.get_cycle_status_airflow_status()}")
        print(f"cool down: {dr.get_cycle_status_cool_down()}")
        print(f"damp: {dr.get_cycle_status_damp()}")
        print(f"drying: {dr.get_cycle_status_drying()}")
        print(f"limited cycle: {dr.get_cycle_status_limited_cycle()}")
        print(f"sensing: {dr.get_cycle_status_sensing()}")
        print(f"static reduce: {dr.get_cycle_status_static_reduce()}")
        print(f"steaming: {dr.get_cycle_status_steaming()}")
        print(f"wet: {dr.get_cycle_status_wet()}")
        print(f"cycle count: {dr.get_odometer_status_cycle_count()}")
        print(f"running hours: {dr.get_odometer_status_running_hours()}")
        print(f"total hours: {dr.get_odometer_status_total_hours()}")
        print(f"isp check: {dr.get_wifi_status_isp_check()}")
        print(f"rssi antenna diversity: {dr.get_wifi_status_rssi_antenna_diversity()}")

        print(f"set dryness: {dr.get_dryness()}")
        print(f"set manual dry time: {dr.get_manual_dry_time()}")
        print(f"set cycle select: {dr.get_cycle_select()}")

    def attr_upd() -> None:
        print("Attributes updated")

    dr.register_attr_callback(attr_upd)

    loop = True
    while loop:
        print_menu()
        choice = await aioconsole.ainput("Enter your choice: ")

        if choice == "p":
            print_status(dr)
        elif choice == "u":
            await dr.fetch_data()
            print_status(dr)
        elif choice == "v":
            print(dr._data_dict)
        elif choice == "c":
            cmd = await aioconsole.ainput("Command: ")
            val = await aioconsole.ainput("Value: ")
            await dr.send_attributes({cmd: val})
        elif choice == "q":
            print("Bye")
            loop = False
        else:
            print("Wrong option selection. Enter any key to try again..")

    dr.unregister_attr_callback(attr_upd)
