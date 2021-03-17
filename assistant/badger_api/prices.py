import requests
from assistant.badger_api.config import urls

def fetch_sett_ppfs():
    response = requests.get("{}/setts".format(urls["staging"]))
    result = response.json()
    return result

def fetch_token_prices():
    response = requests.get("{}/prices".format(urls["staging"]))
    result = response.json()
    return result