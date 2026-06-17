import os

import requests


class Api:
    def __init__(self):
        self.token = None
        self.api_url = f'https://{os.environ["API_HOSTNAME"]}:443'

    def login(self):
        auth_data = {
            'username': (None, os.environ['API_SYSTEM_USERNAME']),
            'password': (None, os.environ['API_SYSTEM_PASSWORD'])
        }
        response = requests.request(
            'POST',
            f'{self.api_url}/auth/jwt/login',
            files=auth_data,
            verify=os.environ['API_ROOT_CA'],
            timeout=10)
        response.raise_for_status()
        self.token = response.json()['access_token']

    def get(self, path, _retried=False):
        headers = {
            'authorization': f'Bearer {self.token}'
        }
        response = requests.get(
            f'{self.api_url}{path}',
            headers=headers,
            verify=os.environ['API_ROOT_CA'],
            timeout=10)
        if response.status_code == 401 and not _retried:
            # one-shot re-login retry; avoid unbounded recursion on persistent 401
            self.login()
            return self.get(path, _retried=True)
        return response
