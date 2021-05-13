from helpers.registry import registry
import requests
from helpers.console_utils import console
from brownie import web3


def address_to_id(token_address):
    checksummed = web3.toChecksumAddress(token_address)
    if checksummed == web3.toChecksumAddress(registry.tokens.wbtc):
        return "wrapped-bitcoin"
    if checksummed == web3.toChecksumAddress(registry.tokens.badger):
        return "badger-dao"
    if checksummed == web3.toChecksumAddress(registry.tokens.digg):
        return "digg"
    else:
        assert False


def fetch_usd_value(token_address, amount):
    price = fetch_usd_price(address_to_id(token_address))
    return price * amount


def fetch_daily_twap(token_address):
    id = address_to_id(token_address)

    url = "https://api.coingecko.com/api/v3/coins/" + id
    params = "?tickers=true&community_data=false&developer_data=false&sparkline=false"

    r = requests.get(url, params)
    data = r.json()
    market_data = data["market_data"]
    console.print(market_data)
    return market_data


def fetch_usd_price(token_address):
    id = address_to_id(token_address)
    url = "https://api.coingecko.com/api/v3/coins/" + id
    params = "?tickers=false&community_data=false&developer_data=false&sparkline=false"

    r = requests.get(url, params)
    data = r.json()
    usd_price = data["market_data"]["current_price"]["usd"]
    console.print(usd_price)
    return usd_price


def fetch_usd_price_eth():
    url = "https://api.coingecko.com/api/v3/coins/" + "ethereum"
    params = "?tickers=false&community_data=false&developer_data=false&sparkline=false"

    r = requests.get(url, params)
    data = r.json()
    usd_price = data["market_data"]["current_price"]["usd"]
    console.print(usd_price)
    return usd_price
