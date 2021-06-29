import requests
from assistant.badger_api.config import urls

def fetch_claimable_balances(address):
    response = requests.get("{}/accounts/{}".format(
        urls["staging"],
        address
    )).json()
    claimableBalances = response.get("claimableBalances",[])
    return claimableBalances