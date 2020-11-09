import requests
import logging
import json
from datetime import datetime, timedelta, timedelta

LOGGER = logging.getLogger(__name__)


class Auth():
    def __init__(self, username, password):
        self._auth_dict = None
        self._username = username
        self._password = password
        # TODO: make async and handle http errors during auth
        self._load_auth_data()

    def _load_auth_data(self, ):
        auth_json_file = "auth.json"
        auth_dict = {}
        try:
            with open(auth_json_file, 'r') as f:
                LOGGER.debug("Loading auth from file")
                auth_dict = json.load(f)
        except FileNotFoundError:
            pass

        curr_timestamp = datetime.now().timestamp()
        if "access_token" not in auth_dict or "expire_date" not in auth_dict or auth_dict["expire_date"] < curr_timestamp:
            refresh_token = auth_dict.get('refresh_token', None)
            fetched_auth_data = self._do_auth(refresh_token)
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

        self._auth_dict = auth_dict

    def _do_auth(self, refresh_token=None):
        auth_url = 'https://api.whrcloud.eu/oauth/token'
        auth_header = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Brand': 'Whirlpool',
            'WP-CLIENT-REGION': 'EMEA',
            'WP-CLIENT-BRAND': 'WHIRLPOOL',
            'WP-CLIENT-COUNTRY': 'EN'
        }

        auth_data = {
            'client_id': 'whirlpool_android',
            'client_secret': 'i-eQ8MD4jK4-9DUCbktfg-t_7gvU-SrRstPRGAYnfBPSrHHt5Mc0MFmYymU2E2qzif5cMaBYwFyFgSU6NTWjZg',
        }

        if refresh_token:
            LOGGER.debug("Fetching auth with refresh token")
            auth_data.update({
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
            })
        else:
            LOGGER.debug("Fetching auth with user/pass")
            auth_data.update({
                'grant_type': 'password',
                'username': self._username,
                'password': self._password,
            })

        with requests.session() as s:
            r = s.post(auth_url, data=auth_data, headers=auth_header)
            LOGGER.debug("Auth status: " + str(r.status_code))
            if r.status_code == 200:
                return json.loads(r.text)
            elif refresh_token:
                return self._do_auth(refresh_token=None)

    def get_access_token(self):
        return self._auth_dict["access_token"]

    def get_said_list(self):
        return self._auth_dict["SAID"]
