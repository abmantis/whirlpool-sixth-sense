import json

import aioconsole

from whirlpool.dryer import Dryer


async def show_dryer_menu(dr: Dryer) -> None:
    def print_menu():
        print("\n")
        print(30 * "-", "MENU", 30 * "-")
        print("u. Update status from server")
        print("p. Print status")
        print("v. Print raw status")
        print("c. Custom command")
        print("q. Exit")
        print(67 * "-")

    def print_status(dr: Dryer):
        print(f"online: {dr.get_online()}")
        print(f"state: {dr.get_machine_state()}")
        print(f"door open: {dr.get_door_open()}")
        print(f"est time remaining: {dr.get_est_time_remaining()}")
        print(f"extra power changeable: {dr.get_extra_power_changeable()}")
        print(f"steam changeable: {dr.get_steam_changeable()}")
        print(f"cycle select: {dr.get_cycle_changeable()}")
        print(f"dryness: {dr.get_dryness_changeable()}")
        print(f"manual dry time: {dr.get_manual_dry_time_changeable()}")
        print(f"static guard: {dr.get_static_guard_changeable()}")
        print(f"temperature: {dr.get_temperature_changeable()}")
        print(f"wrinkle shield: {dr.get_wrinkle_shield_changeable()}")
        print(f"airflow status: {dr.get_cycle_status_airflow_status()}")
        print(f"cool down: {dr.get_cycle_status_cool_down()}")
        print(f"damp: {dr.get_cycle_status_damp()}")
        print(f"drying: {dr.get_cycle_status_drying()}")
        print(f"limited cycle: {dr.get_cycle_status_limited_cycle()}")
        print(f"sensing: {dr.get_cycle_status_sensing()}")
        print(f"static reduce: {dr.get_cycle_status_static_reduce()}")
        print(f"steaming: {dr.get_cycle_status_steaming()}")
        print(f"wet: {dr.get_cycle_status_wet()}")
        print(f"cycle count: {dr.get_cycle_count()}")

        print(f"set dryness: {dr.get_dryness()}")
        print(f"set manual dry time: {dr.get_manual_dry_time()}")
        print(f"set cycle select: {dr.get_cycle()}")
        print(f"set temperature: {dr.get_temperature()}")
        print(f"set wrinkle shield: {dr.get_wrinkle_shield()}")

    def attr_upd():
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
            print(json.dumps(dr._data_dict, indent=4))
        elif choice == "c":
            cmd = await aioconsole.ainput("Command: ")
            val = await aioconsole.ainput("Value: ")
            await dr.send_attributes({cmd: val})
        elif choice == "q":
            print("Bye")
            loop = False
        else:
            print("Wrong option selection. Enter any key to try again..")
