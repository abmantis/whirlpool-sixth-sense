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
        print(f"door open: {dr.get_door_open()}")
        print(f"est time remaining: {dr.get_est_time_remaining()}")
        print(f"extra power changeable: {dr.get_status_extra_power_changeable()}")
        print(f"steam changeable: {dr.get_status_extra_steam_changeable()}")
        print(f"cycle select: {dr.get_status_cycle_select()}")
        print(f"dryness: {dr.get_status_dryness()}")
        print(f"manual dry time: {dr.get_status_manual_dry_time()}")
        print(f"static guard: {dr.get_status_static_guard()}")
        print(f"temperature: {dr.get_status_temperature()}")
        print(f"wrinkle shield: {dr.get_status_wrinkle_shield()}")
        print(f"airflow status: {dr.get_airflow_status()}")
        print(f"cool down: {dr.get_cool_down()}")
        print(f"damp: {dr.get_damp()}")
        print(f"drying: {dr.get_drying()}")
        print(f"limited cycle: {dr.get_limited_cycle()}")
        print(f"sensing: {dr.get_sensing()}")
        print(f"static reduce: {dr.get_static_reduce()}")
        print(f"steaming: {dr.get_steaming()}")
        print(f"wet: {dr.get_wet()}")
        print(f"cycle count: {dr.get_cycle_count()}")
        print(f"running hours: {dr.get_running_hours()}")
        print(f"total hours: {dr.get_total_hours()}")
        print(f"isp check: {dr.get_isp_check()}")
        print(f"rssi antenna diversity: {dr.get_rssi_antenna_diversity()}")

        print(f"set dryness: {dr.get_dryness()}")
        print(f"set manual dry time: {dr.get_manual_dry_time()}")
        print(f"set cycle select: {dr.get_cycle_select()}")

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
