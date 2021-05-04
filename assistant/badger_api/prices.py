import requests
from assistant.badger_api.config import urls


def fetch_ppfs():
    response = requests.get("{}/setts".format(urls["staging"])).json()
    badger = [s for s in response if s["asset"] == "BADGER"][0]
    digg = [s for s in response if s["asset"] == "DIGG"][0]
    return badger["ppfs"], digg["ppfs"]


def fetch_token_prices():
    response = requests.get("{}/prices".format(urls["staging"])).json()
    return response
