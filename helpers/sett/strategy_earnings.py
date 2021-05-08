from brownie import *
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem
from helpers.registry.eth_registry import curve_registry, badger_registry, sushi_registry, digg_registry, eth_registry
import requests

console = Console()

endpoint = "https://api.0x.org/"
endpoint_bsc = "https://bsc.api.0x.org/"

# returns harvest earnings denominated in eth
def get_harvest_earnings(badger: BadgerSystem, strategy: Contract, key: str, overrides):
  token = get_symbol(badger, strategy)
  if not token:
    console.log("token for strategy at", strategy.address, "not found")
    return 0

  token_address = eth_registry.tokens[token.lower()]
  if not type(token_address) == str:
    console.log("address for token", token, "not found")
    return 0

  crv_gauge = Contract.from_explorer(strategy.gauge())
  earnings = crv_gauge.claimable_tokens.call(strategy.address, overrides)

  if earnings > 0: price = get_price(token, sellAmount=earnings)
  else: price = get_price(token)

  token_contract = interface.IERC20(token_address)
  decimals = token_contract.decimals()
  eth_profit = earnings / (10**decimals) * float(price)
  console.log("harvest earnings:", token, "earnings:", earnings, "price:", price, "eth profit:", eth_profit)

  return eth_profit


def get_price(token: str, buyToken="WETH", sellAmount=1000000000000000000, network="eth"):
  """
  get_price uses the 0x api to get the most accurate eth price for the token

  :param token: token ticker, can also be token address
  :param buyToken: token to denominate price in, default is WETH
  :param sellAmount: token amount to sell in base unit, default is 1e18
  :return: eth price of one token
  """ 
  if len(token) == 42:
    # get ticker
    token_contract = interface.IERC20(token)
    token = token_contract.symbol()

  params = "swap/v1/quote?buyToken=" + buyToken + "&sellToken=" + token + "&sellAmount=" + str(sellAmount)
  if network == "bsc":
    r = requests.get(endpoint_bsc + params)
  else:
    r = requests.get(endpoint + params)
  data = r.json()

  if not data.get('guaranteedPrice'):
    console.log(data)
    raise ValueError("Price could not be fetched")

  return data['guaranteedPrice'] 


def get_symbol(badger: BadgerSystem, strategy: str):
  if is_crv_strategy(badger, strategy):
    return curve_registry.symbol
  if is_badger_strategy(badger, strategy):
    return badger_registry.symbol
  if is_digg_strategy(badger, strategy):
    return digg_registry.symbol
  if is_xsushi_strategy(badger, strategy):
    return sushi_registry.xSushiSymbol


def is_crv_strategy(badger: BadgerSystem, strategy: str):
  return strategy == badger.getStrategy("native.renCrv") or \
    strategy == badger.getStrategy("native.sbtcCrv") or \
    strategy == badger.getStrategy("native.tbtcCrv")


def is_badger_strategy(badger: BadgerSystem, strategy: str):
  return strategy == badger.getStrategy("native.uniBadgerWbtc") or \
    strategy == badger.getStrategy("native.sushiBadgerWbtc")


def is_digg_strategy(badger: BadgerSystem, strategy: str):
  return strategy == badger.getStrategy("native.uniDiggWbtc") or \
    strategy == badger.getStrategy("native.sushiDiggWbtc")


def is_xsushi_strategy(badger: BadgerSystem, strategy: str):
  return strategy == badger.getStrategy("native.sushiWbtcEth")
