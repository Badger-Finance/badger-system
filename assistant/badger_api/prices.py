import requests
from assistant.badger_api.config import urls

def fetch_sett_ppfs(token):
    response = requests.get("{}/setts".format(urls["staging"]))
    result = response.json()
    sett = list(filter( lambda sett: sett["underlyingToken"] == token,result))
    return sett[0]["ppfs"]

def fetch_token_price(token):
    response = requests.get("{}/prices".format(urls["staging"]))
    result = response.json()
    return result[token]