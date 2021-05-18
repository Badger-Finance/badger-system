from brownie import *
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem
from helpers.network import network_manager
from helpers.registry.eth_registry import curve_registry, badger_registry, sushi_registry, digg_registry, harvest_registry, eth_registry
from helpers.registry.bsc_registry import bsc_registry
import requests

console = Console()
curr_network = network_manager.get_active_network()

# returns harvest earnings denominated in eth
def get_harvest_earnings(badger: BadgerSystem, strategy: Contract, key: str, overrides):
  token = get_symbol(key)
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

  elif is_xsushi_strategy(key) or is_pancake_strategy(key):
    harvest_data = strategy.harvest.call(overrides)
    earnings = harvest_data[0]
  
  else:
    console.log('Profit estimation not supported yet for strategy at', strategy.address)
    return 'skip'

  if earnings > 0: price = get_price(token_address, sellAmount=earnings)
  else: price = get_price(token_address)

  token_contract = interface.IERC20(token_address)
  decimals = token_contract.decimals()
  eth_profit = earnings / (10**decimals) * float(price)

  if curr_network == "bsc":
    console.log("harvest token:", token, "earnings:", earnings, "price in bnb:", price, "bnb profit:", eth_profit)
  elif curr_network == "eth":
    console.log("harvest token:", token, "earnings:", earnings, "price in eth:", price, "eth profit:", eth_profit)

  return eth_profit


def get_price(token: str, sellAmount=1000000000000000000):
  """
  get_price uses the 0x api to get the most accurate eth price for the token

  :param token: token ticker or token address
  :param buyToken: token to denominate price in, default is WETH
  :param sellAmount: token amount to sell in base unit, default is 1e18
  :return: eth price of one token
  """

  if curr_network == "bsc":
    endpoint = "https://bsc.api.0x.org/"
    buyToken="WBNB"
  elif curr_network == "eth":
    endpoint = "https://api.0x.org/"
    buyToken="WETH"
  else:
    raise ValueError("Unrecognized network")

  params = "swap/v1/quote?buyToken=" + buyToken + "&sellToken=" + token + "&sellAmount=" + str(sellAmount)
  r = requests.get(endpoint + params)
  data = r.json()

  if not data.get('guaranteedPrice'):
    console.log(data)
    raise ValueError("Price could not be fetched")

  return data['guaranteedPrice'] 


def get_symbol(key: str):
  if curr_network == 'eth':
    if is_crv_strategy(key):
      return curve_registry.symbol
    if is_badger_strategy(key):
      return badger_registry.symbol
    if is_digg_strategy(key):
      return digg_registry.symbol
    if is_xsushi_strategy(key):
      return sushi_registry.symbol_xsushi
    if is_farm_strategy(key):
      return harvest_registry.symbol
  elif curr_network == 'bsc':
    if is_pancake_strategy(key):
      return bsc_registry.pancake.symbol


def is_farm_strategy(key: str):
  return key in ['harvest.renCrv']


def is_crv_strategy(key: str):
  return key in ["native.renCrv", "native.sbtcCrv", "native.tbtcCrv"]


def is_badger_strategy(key: str):
  return key in ["native.uniBadgerWbtc", "native.sushiBadgerWbtc"]


def is_digg_strategy(key: str):
  return key in ["native.uniDiggWbtc", "native.sushiDiggWbtc"]


def is_xsushi_strategy(key: str):
  return key in ["native.sushiWbtcEth"]


def is_pancake_strategy(key: str):
  return key in ["native.pancakeBnbBtcb", "native.bBadgerBtcb", "native.bDiggBtcb"]


def get_address(token: str):
  if curr_network == 'eth':
    if token == 'XSUSHI':
      return eth_registry.tokens.xSushi
    return eth_registry.tokens[token.lower()]
  elif curr_network == 'bsc':
    if token == 'Cake':
      return bsc_registry.pancake.cake
    else:
      return bsc_registry.tokens[token.lower()]
    