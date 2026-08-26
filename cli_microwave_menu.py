import json
from datetime import datetime

import aioconsole

from whirlpool.microwave import (
    HoodFanSpeed,
    HoodLightColor,
    HoodLightLevel,
    Microwave,
    Recipe,
)

RECIPES = {
    "m": Recipe.Microwave,
    "r": Recipe.Reheat,
    "d": Recipe.Defrost,
    "s": Recipe.Soften,
}

HOOD_FAN_SPEEDS = {
    "o": HoodFanSpeed.Off,
    "l": HoodFanSpeed.Low,
    "m": HoodFanSpeed.Medium,
    "h": HoodFanSpeed.High,
    "b": HoodFanSpeed.Boost,
}

HOOD_LIGHT_LEVELS = {
    "o": HoodLightLevel.Off,
    "l": HoodLightLevel.Low,
    "m": HoodLightLevel.Medium,
    "h": HoodLightLevel.High,
}

HOOD_LIGHT_COLORS = {
    "w": HoodLightColor.WarmWhite,
    "n": HoodLightColor.NaturalWhite,
    "c": HoodLightColor.CoolWhite,
}


async def show_microwave_menu(mw: Microwave) -> None:
    def print_menu():
        print("\n")
        print(30 * "-", "MENU", 30 * "-")
        print("u. Update status from server")
        print("L. Cavity light toggle")
        print("t. Set cooking recipe/power/duration")
        print("o. Stop/cancel cooking")
        if mw.supports_hood_fan():
            print("f. Set hood fan speed")
        if mw.supports_hood_light_level():
            print("h. Set hood light level")
        if mw.supports_hood_light_color():
            print("c. Set hood light color")
        if mw.supports_control_lock():
            print("l. Control lock toggle")
        if mw.supports_quiet_mode():
            print("Q. Toggle quiet mode")
        if mw.supports_sabbath_mode():
            print("s. Toggle Sabbath mode")
        print("p. Print status")
        print("v. Print raw status")
        print("q. Exit")
        print(67 * "-")

    def print_status(mw: Microwave):
        print("online: " + str(mw.get_online()))
        print("cavity state: " + str(mw.get_cavity_state()))
        print("door status: " + str(mw.get_door_status()))
        print("door locked: " + str(mw.get_door_locked()))
        print("cavity light: " + str(mw.get_cavity_light()))
        print(
            "display temperature: "
            + str(mw.get_display_temperature())
            + " "
            + str(mw.get_display_temperature_unit())
        )
        print("turntable enabled: " + str(mw.get_turntable_enabled()))
        print("active recipe id: " + str(mw.get_active_recipe_id()))
        print("recipe execution state: " + str(mw.get_recipe_execution_state()))
        print("power level: " + str(mw.get_mwo_power_level()))
        print("cook timer state: " + str(mw.get_cook_timer_state()))
        time_complete = mw.get_cook_timer_time_complete()
        print(
            "cook timer time complete: "
            + (
                datetime.fromtimestamp(time_complete).isoformat()
                if time_complete
                else str(time_complete)
            )
        )
        print("cook timer total (seconds): " + str(mw.get_cook_timer_total_seconds()))
        print("remote start enabled: " + str(mw.get_remote_start_enabled()))
        if mw.supports_hood_fan():
            print("hood fan speed: " + str(mw.get_hood_fan_speed()))
        if mw.supports_hood_light_level():
            print("hood light level: " + str(mw.get_hood_light_level()))
        if mw.supports_hood_light_color():
            print("hood light color: " + str(mw.get_hood_light_color()))
        if mw.supports_control_lock():
            print("control lock: " + str(mw.get_control_locked()))
        if mw.supports_quiet_mode():
            print("quiet mode: " + str(mw.get_quiet_mode()))
        if mw.supports_sabbath_mode():
            print("sabbath mode: " + str(mw.get_sabbath_mode()))

    def attr_upd():
        print("Attributes updated")

    mw.register_attr_callback(attr_upd)

    loop = True
    while loop:
        print_menu()
        choice = await aioconsole.ainput("Enter your choice: ")

        if choice == "p":
            print_status(mw)
        elif choice == "L":
            await mw.set_cavity_light(not mw.get_cavity_light())
        elif choice == "t":
            print(
                """Recipes:
            m: Microwave
            r: Reheat
            d: Defrost
            s: Soften
            """
            )
            recipe = RECIPES.get(await aioconsole.ainput("Enter recipe: "))
            if recipe is None:
                print("Invalid recipe")
                continue
            duration = await aioconsole.ainput("Enter cook duration (seconds): ")
            power_level = await aioconsole.ainput(
                "Enter power level (empty for recipes with a fixed power level): "
            )
            try:
                await mw.set_cook(
                    recipe=recipe,
                    duration_seconds=int(duration),
                    power_level=int(power_level) if power_level else None,
                )
            except ValueError as err:
                print(f"Invalid cook settings: {err}")
        elif choice == "o":
            await mw.stop_cook()
        elif choice == "f":
            print(
                """Hood fan speeds:
            o: Off
            l: Low
            m: Medium
            h: High
            b: Boost
            """
            )
            speed = HOOD_FAN_SPEEDS.get(await aioconsole.ainput("Enter fan speed: "))
            if speed is None:
                print("Invalid fan speed")
                continue
            await mw.set_hood_fan_speed(speed)
        elif choice == "h":
            print(
                """Hood light levels:
            o: Off
            l: Low
            m: Medium
            h: High
            """
            )
            level = HOOD_LIGHT_LEVELS.get(
                await aioconsole.ainput("Enter light level: ")
            )
            if level is None:
                print("Invalid light level")
                continue
            await mw.set_hood_light_level(level)
        elif choice == "c":
            print(
                """Hood light colors:
            w: Warm white
            n: Natural white
            c: Cool white
            """
            )
            color = HOOD_LIGHT_COLORS.get(
                await aioconsole.ainput("Enter light color: ")
            )
            if color is None:
                print("Invalid light color")
                continue
            await mw.set_hood_light_color(color)
        elif choice == "l":
            await mw.set_control_locked(not mw.get_control_locked())
        elif choice == "Q":
            await mw.set_quiet_mode(not mw.get_quiet_mode())
        elif choice == "s":
            await mw.set_sabbath_mode(not mw.get_sabbath_mode())
        elif choice == "u":
            await mw.fetch_data()
            print_status(mw)
        elif choice == "v":
            print(json.dumps(mw.get_raw_data(), indent=4))
        elif choice == "q":
            print("Bye")
            loop = False
        else:
            print("Wrong option selection. Enter any key to try again..")
