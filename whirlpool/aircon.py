import requests
import base64
import re
import json
from datetime import datetime, timedelta, timedelta

ATTR_ONLINE = "Online"
ATTR_MODE = "Cavity_OpStatusMode"
ATTR_TEMP = "Sys_OpStatusDisplayTemp",
ATTR_HUMID = "Sys_OpStatusDisplayHumidity",

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

ATTRVAL_MODE_COOL = "1"
ATTRVAL_MODE_FAN = "2"
ATTRVAL_MODE_HEAT = "3"
ATTRVAL_MODE_SIXTH_SENSE_AIR = "5"
ATTRVAL_MODE_SIXTH_SENSE_HEAT = "6"
ATTRVAL_MODE_SIXTH_SENSE_COOL = "7"

SETVAL_VALUE_OFF = "0"
SETVAL_VALUE_ON = "1"
SETVAL_MODE_COOL = "1"
SETVAL_MODE_FAN = "2"
SETVAL_MODE_HEAT = "3"
SETVAL_MODE_SIXTH_SENSE = "4"
SETVAL_FAN_SPEED_AUTO = "1"
SETVAL_FAN_SPEED_LOW = "2"
SETVAL_FAN_SPEED_MEDIUM = "4"
SETVAL_FAN_SPEED_HIGH = "6"

class Appliance():
    def __init__(self, auth, said):
        self._auth = auth
        self._said = said
        self._data_dict = None

    def _create_headers(self):
        return {
            'Authorization': 'Bearer ' + self._auth.get_access_token(),
            'Content-Type': 'application/json',
            'Host': 'api.whrcloud.eu',
            'User-Agent': 'okhttp/3.12.0',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
        }

    def send_attributes(self, attributes):
        cmd_data = {
            "body": attributes,
            "header":{
                "said": self._said,
                "command": "setAttributes"
            }
        }

        headers = self._create_headers()
        with requests.session() as s:
            r = s.post('https://api.whrcloud.eu/api/v1/appliance/command', headers=headers, json=cmd_data)
            print(r.text)

    def get_attribute_from_fetched_data(self, attribute, updateTime = None):
        if updateTime:
            self._data_dict["attributes"][attribute]["updateTime"]
        return self._data_dict["attributes"][attribute]["value"]

    def fetch_data(self):
        headers = self._create_headers()
        self._data_dict = None
        with requests.session() as s:
            r = s.get('https://api.whrcloud.eu/api/v1/appliance/{0}'.format(self._said), headers=headers)
            self._data_dict = json.loads(r.text)

    #def get_account_id(self, user_details):
        #return user_details["accountId"]

    #def fetch_said(self, account_id):
        #headers = self._create_headers()
        #with requests.session() as s:
            #r = s.get('https://api.whrcloud.eu/api/v1/appliancebyaccount/{0}'.format(accountId), headers=headers)
            #print(r.text)
            #device_said = json.loads(r.text)["accountId"]

    #def fetch_user_details(self):
        #headers = self._create_headers()
        #with requests.session() as s:
            #r = s.get('https://api.whrcloud.eu/api/v1/getUserDetails', headers=headers)
            #return json.loads(r.text)
        #return None

class Aircon(Appliance):
    def __init__(self, auth, said):
        Appliance.__init__(self, auth, said)

    def print_fetched_data(self):
        attrs = [
                "Online",
                "Sys_OpSetPowerOn",
                "Sys_OpSetTargetTemp",
                "Sys_OpSetTargetHumidity",
                "Sys_OpSetSleepMode",
                "Cavity_OpSetHorzLouverSwing",
                "Cavity_OpSetMode",
                "Cavity_OpSetFanSpeed",
                "Cavity_OpSetTurboMode",
                "Sys_OpSetEcoModeEnabled",
                "Sys_OpSetQuietModeEnabled",
                "Cavity_OpStatusMode",
                "Sys_OpStatusDisplayTemp",
                "Sys_OpStatusDisplayHumidity",
            ]

        for a in attrs:
            print(a + ": " + self.get_attribute_from_fetched_data(a))

    def online(self):
        return self._data_dict["Online"]


# ISSUES:
# no recovery found yet (except power cycle): { "message":"Appliance claimed successfully","status":"01" }
# rebooting wifi works: { "message":"Error in command execution or Invalid command","status":"03" }
