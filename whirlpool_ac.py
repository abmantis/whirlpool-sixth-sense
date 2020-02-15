import requests
import base64
import re
import json
from datetime import datetime, timedelta, timedelta

SETTING_REBOOT_WIFI = "XCat_WifiSetRebootWifiCommModule"
SETTING_POWER = "Sys_OpSetPowerOn"
SETTING_TEMP = "Sys_OpSetTargetTemp"
SETTING_HUMIDITY = "Sys_OpSetTargetHumidity"
SETTING_SLEEP_MODE = "Sys_OpSetSleepMode"
SETTING_HORZ_LOUVER_SWING = "Cavity_OpSetHorzLouverSwing"
SETTING_MODE = "Cavity_OpSetMode"
SETTING_FAN_SPEED = "Cavity_OpSetFanSpeed"
SETTING_TURBO_MODE = "Cavity_OpSetTurboMode"
SETTING_ECO_MODE = "Sys_OpSetEcoModeEnabled"
SETTING_QUIET_MODE = "Sys_OpSetQuietModeEnabled"

SET_VALUE_OFF = "0"
SET_VALUE_ON = "1"
SET_MODE_COOL = "1"
SET_MODE_FAN = "2"
SET_MODE_HEAT = "3"
SET_MODE_SIXTH_SENSE = "4"
SET_FAN_SPEED_AUTO = "1"
SET_FAN_SPEED_LOW = "2"
SET_FAN_SPEED_MEDIUM = "4"
SET_FAN_SPEED_HIGH = "6"

def load_auth_data():
    auth_json_file = "auth.json"
    auth_dict = {}
    try:
        with open(auth_json_file, 'r') as f:
            print("Loading auth from file\n")
            auth_dict = json.load(f)
    except FileNotFoundError:
        pass

    curr_timestamp = datetime.now().timestamp()
    if "access_token" not in auth_dict or "expire_date" not in auth_dict or auth_dict["expire_date"] < curr_timestamp: 
        refresh_token = auth_dict.get('refresh_token', None)
        fetched_auth_data = fetch_auth_data(refresh_token)
        auth_dict = {
            "access_token": fetched_auth_data["access_token"],
            "refresh_token": fetched_auth_data["refresh_token"],
            "expire_date": curr_timestamp + fetched_auth_data["expires_in"],
            "accountId": fetched_auth_data["accountId"],
            "SAID": fetched_auth_data["SAID"],
        }
    
    # Writing JSON data
    with open(auth_json_file, 'w') as f:
        json.dump(auth_dict, f)

    return auth_dict

def fetch_auth_data(refresh_token=None):
    auth_url = 'https://api.whrcloud.eu/oauth/token'
    auth_header = {        
        'Brand': 'Whirlpool',
        'WP-CLIENT-REGION': 'EMEA',
        'WP-CLIENT-BRAND': 'WHIRLPOOL',
        'WP-CLIENT-COUNTRY': 'IT',
        'Host': 'api.whrcloud.eu',
        'User-Agent': 'okhttp/3.12.0',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
    }

    auth_data = {
        'client_id': 'syntel',
        'client_secret': 'syntel123$',
    } 

    if refresh_token:
        print("Fetching auth with refresh token")
        auth_data.update({
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
        })
    else:
        print("Fetching auth with user/pass")
        auth_data.update({
            'grant_type': 'password',
            'username': 'x',
            'password': 'y',
        })
    
    with requests.session() as s:   
        r = s.post(auth_url, data=auth_data, headers=auth_header)
        print("Auth status: " + str(r.status_code))

        return json.loads(r.text)


def create_headers(access_token):
    return {
        'Authorization': 'Bearer ' + access_token,
        'Content-Type': 'application/json',
        'Host': 'api.whrcloud.eu',
        'User-Agent': 'okhttp/3.12.0',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
    }


#def fetch_said(access_token, account_id):
    #headers = create_headers(access_token)
    #with requests.session() as s:   
        #r = s.get('https://api.whrcloud.eu/api/v1/appliancebyaccount/{0}'.format(accountId), headers=headers)
        #print(r.text)
        #device_said = json.loads(r.text)["accountId"]

def fetch_user_details(access_token):
    headers = create_headers(access_token)
    
    with requests.session() as s:   
        r = s.get('https://api.whrcloud.eu/api/v1/getUserDetails', headers=headers)
        #print(r.text)
        return json.loads(r.text)
    return None


def fetch_appliance(access_token, said):
    headers = create_headers(access_token)
    with requests.session() as s:   
        r = s.get('https://api.whrcloud.eu/api/v1/appliance/{0}'.format(said), headers=headers)
        return json.loads(r.text)
    return None


def get_account_id(user_details):
    return user_details["accountId"]


def call_appliance_command(access_token, said, settings):
    cmd_data = {
        "body": settings,
#        "body":{
#            #"XCat_WifiSetRebootWifiCommModule": "1",
#            "Sys_OpSetPowerOn": "0",
#            "Sys_OpSetTargetTemp": "180",
#            "Sys_OpSetTargetHumidity": "40",
#            "Sys_OpSetSleepMode": "0",
#            "Cavity_OpSetHorzLouverSwing": "0",
#            "Cavity_OpSetMode": "3", # 1 - Cool, 2 - Fan, 3 - Heat, 4 - Sixth sense
#            "Cavity_OpSetFanSpeed": "2", # 1 - Auto, 2 - Low, 4 - Medium, 6 - High
#            "Cavity_OpSetTurboMode": "0",
#            "Sys_OpSetEcoModeEnabled": "0",
#            "Sys_OpSetQuietModeEnabled": "0",
#        },
        "header":{
            "said": said,
            "command": "setAttributes"
        }
    }
    
    headers = create_headers(access_token)
    with requests.session() as s:   
        r = s.post('https://api.whrcloud.eu/api/v1/appliance/command', headers=headers, json=cmd_data)
        print(r.text)

def get_setting_from_appliance_data(data, setting):
    return data["attributes"][setting]["value"]

def print_appliance_data(data):
    attrs = [
            "Online",
            "XCat_WifiSetRebootWifiCommModule",
            "XCat_WifiSetPublishApplianceState",
            "Sys_OpSetPowerOn", 
            "Sys_OpSetTargetTemp", 
            "Sys_OpSetTargetHumidity",
            "Sys_OpSetSleepMode", 
            "Cavity_OpSetHorzLouverSwing", 
            "Cavity_OpSetMode", 
            "Cavity_OpSetFanSpeed",
            "Cavity_OpSetTurboMode",
            "Sys_OpSetEcoModeEnabled",
            "Sys_OpStatusDisplayTemp",
            "Sys_OpStatusDisplayHumidity",
            "Sys_OpSetQuietModeEnabled",
        ]

    for a in attrs:
        print(a + ": " + get_setting_from_appliance_data(data, a))


auth_data = load_auth_data()
access_token = auth_data["access_token"]
said = auth_data["SAID"][0]

def print_menu():
    print('\n')
    print(30 * "-" , "MENU" , 30 * "-")
    print("1. Turn on")
    print("0. Turn off")
    print("+. Temp up")
    print("-. Temp down")
    print("p. Print status")
    print("r. Restart wifi")
    print("q. Exit")
    print(67 * "-")
  
loop=True      
  
while loop:    
    print_menu()
    choice = input("Enter your choice: ")
     
    if choice=='1':
        call_appliance_command(access_token, said, {SETTING_POWER: SET_VALUE_ON})
    elif choice=='0':
        call_appliance_command(access_token, said, {SETTING_POWER: SET_VALUE_OFF})
    elif choice=='+':
        temp = int(get_setting_from_appliance_data(fetch_appliance(access_token, said), SETTING_TEMP))
        temp = temp + 10
        call_appliance_command(access_token, said, {SETTING_TEMP: str(temp)})
    elif choice=='-':
        temp = int(get_setting_from_appliance_data(fetch_appliance(access_token, said), SETTING_TEMP))
        temp = temp - 10
        call_appliance_command(access_token, said, {SETTING_TEMP: str(temp)})
    elif choice=='p':
        print_appliance_data(fetch_appliance(access_token, said))
    elif choice=='r':
        call_appliance_command(access_token, said, {SETTING_REBOOT_WIFI: SET_VALUE_ON})
    elif choice=='q':
        print("Bye")
        loop=False
    else:
        print("Wrong option selection. Enter any key to try again..")

