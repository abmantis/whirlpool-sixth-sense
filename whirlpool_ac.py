import argparse

from whirlpool.aircon import *
from whirlpool.auth import Auth

parser = argparse.ArgumentParser()
parser.add_argument('-e', '--email', help='Email address')
parser.add_argument('-p', '--password', help='Password')
args = parser.parse_args()

auth = Auth(args.email, args.password)
ac = Aircon(auth, auth.get_said_list()[0])

def print_menu():
    print('\n')
    print(30 * "-" , "MENU" , 30 * "-")
    print("1. Turn on")
    print("0. Turn off")
    print("+. Temp up")
    print("-. Temp down")
    print("C. Mode: Cool")
    print("H. Mode: Heat")
    print("F. Mode: Fan")
    print("S. Mode: Sixth Sense")
    print("p. Print status")
    print("v. Print raw status")
    print("r. Restart wifi")
    print("c. Custom command")
    print("q. Exit")
    print(67 * "-")

loop=True

while loop:
    print_menu()
    choice = input("Enter your choice: ")

    if choice=='1':
        ac.turn_on()
    elif choice=='0':
        ac.turn_off()
    elif choice=='+':
        ac.fetch_data()
        temp = int(ac.get_attribute_from_fetched_data(SETTING_TEMP)) + 10
        ac.set_temp(temp)
    elif choice=='-':
        ac.fetch_data()
        temp = int(ac.get_attribute_from_fetched_data(SETTING_TEMP)) - 10
        ac.set_temp(temp)
    elif choice=='C':
        ac.set_mode(Modes.Cool)
    elif choice=='H':
        ac.set_mode(Modes.Heat)
    elif choice=='F':
        ac.set_mode(Modes.Fan)
    elif choice=='S':
        ac.set_mode(Modes.SixthSense)
    elif choice=='p':
        ac.fetch_data()
        ac.print_fetched_data()
    elif choice=='v':
        ac.fetch_data()
        print(ac._data_dict)
    elif choice=='r':
        ac.send_attributes({SETTING_REBOOT_WIFI: SETVAL_VALUE_ON})
    elif choice=='c':
        cmd = input("Command: ")
        val = input("Value: ")
        ac.send_attributes({cmd: val})
    elif choice=='q':
        print("Bye")
        loop=False
    else:
        print("Wrong option selection. Enter any key to try again..")


# ISSUES:
# no recovery found yet (waiting X minutes?): { "message":"Appliance claimed successfully","status":"01" }
# rebooting wifi works: { "message":"Error in command execution or Invalid command","status":"03" }
