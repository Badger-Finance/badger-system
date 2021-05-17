from brownie import *
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem
from helpers.registry.eth_registry import curve_registry, badger_registry, sushi_registry, digg_registry, harvest_registry, eth_registry
import requests

console = Console()

endpoint = "https://api.0x.org/"
endpoint_bsc = "https://bsc.api.0x.org/"

# returns harvest earnings denominated in eth
def get_harvest_earnings(badger: BadgerSystem, strategy: Contract, key: str, overrides):
  token = get_symbol(badger, strategy)
  if not token:
    console.log("token for strategy at", strategy.address, "not found")
    return 'skip'

  token_address = get_address(token)
  if not type(token_address) == str:
      console.log("address for token", token, "not found")
      return 'skip'

  if key == 'harvest.renCrv':
    metafarm = "0xae024f29c26d6f71ec71658b1980189956b0546d"
    earnings = Contract.from_explorer(metafarm).balanceOf(strategy.address)
    token_address = harvest_registry.farmToken

  elif key.endswith('Crv'):
    crv_gauge = Contract.from_explorer(strategy.gauge())
    earnings = crv_gauge.claimable_tokens.call(strategy.address, overrides)

  elif is_xsushi_strategy(badger, strategy):
    harvest_data = strategy.harvest.call(overrides)
    earnings = harvest_data[0]
  
  else:
    console.log('Profit estimation not supported yet for strategy at', strategy.address)
    return 'skip'

  if earnings > 0: price = get_price(token_address, sellAmount=earnings)
  else: price = get_price(token)

  token_contract = interface.IERC20(token_address)
  decimals = token_contract.decimals()
  eth_profit = earnings / (10**decimals) * float(price)
  console.log("harvest token:", token, "earnings:", earnings, "price:", price, "eth profit:", eth_profit)

  return eth_profit


def get_price(token: str, buyToken="WETH", sellAmount=1000000000000000000, network="eth"):
  """
  get_price uses the 0x api to get the most accurate eth price for the token

  :param token: token ticker or token address
  :param buyToken: token to denominate price in, default is WETH
  :param sellAmount: token amount to sell in base unit, default is 1e18
  :return: eth price of one token
  """

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
    return sushi_registry.symbol_xsushi
  if is_farm_strategy(badger, strategy):
    return harvest_registry.symbol


def is_farm_strategy(badger: BadgerSystem, strategy: str):
  return strategy == badger.getStrategy('harvest.renCrv')


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


def get_address(token: str):
  if token == 'XSUSHI':
    return eth_registry.tokens.xSushi
  return eth_registry.tokens[token.lower()]