from brownie import *
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem
from helpers.network import network_manager
from helpers.registry.eth_registry import (
    curve_registry,
    badger_registry,
    sushi_registry,
    digg_registry,
    harvest_registry,
    eth_registry,
)
from helpers.registry.bsc_registry import bsc_registry
import requests

console = Console()
curr_network = network_manager.get_active_network()


def get_tend_earnings_manager(
    badger: BadgerSystem, strategy: Contract, key: str, overrides
):
    """
    get the estimated profit from tending the strategy via the manager

    :param strategy: the strategy to be tended
    :param key: key for the strategy
    :param overrides: transaction overrides
    :return: profit in eth/bnb or 'skip' if the strategy can't be estimated
    """

    (token, token_address) = token_data(key, True)
    if not token or not token_address:
        return "skip"

    try:
        tend_data = strategy.tend.call(
            {"from": badger.badgerRewardsManager, "gas_limit": overrides["gas_limit"]}
        )
        earnings = tend_data[0]

    except Exception as ex:
        console.log("estimation failed", key, ex)
        return 0

    return calc_profit(earnings, token_address, token)


def get_tend_earnings(strategy: Contract, key: str, overrides):
    """
    get the estimated profit from tending the strategy

    :param strategy: the strategy to be tended
    :param key: key for the strategy
    :param overrides: transaction overrides
    :return: profit in eth/bnb or 'skip' if the strategy can't be estimated
    """

    (token, token_address) = token_data(key, True)
    if not token or not token_address:
        return "skip"

    try:
        tend_data = strategy.tend.call(overrides)
        earnings = tend_data[0]

    except Exception as ex:
        console.log("estimation failed", key, ex)
        return 0

    return calc_profit(earnings, token_address, token)


# returns harvest earnings denominated in eth/bnb
def get_harvest_earnings(strategy: Contract, key: str, overrides):
    """
    get the estimated profit from harvesting the strategy

    :param strategy: the strategy to be harvested
    :param key: key for the strategy
    :param overrides: transaction overrides
    :return: profit in eth/bnb or 'skip' if the strategy can't be estimated
    """

    (token, token_address) = token_data(key, False)
    if not token or not token_address:
        return "skip"

    if is_farm_strategy(key):
        earnings = Contract.from_explorer(harvest_registry.farms.farm).balanceOf(
            strategy.address
        )

    elif is_crv_strategy(key):
        crv_gauge = Contract.from_explorer(strategy.gauge())
        earnings = crv_gauge.claimable_tokens.call(strategy.address, overrides)

    elif is_xsushi_strategy(key) or is_pancake_strategy(key):
        harvest_data = strategy.harvest.call(overrides)
        earnings = harvest_data[0]

    else:
        console.log(
            "Profit estimation not supported yet for strategy at", strategy.address
        )
        return "skip"

    return calc_profit(earnings, token_address, token)


def get_price(token: str, sellAmount=1000000000000000000):
    """
    get_price uses the 0x api to get the most accurate eth price for the token

    :param token: token ticker or token address
    :param buyToken: token to denominate price in, default is WETH
    :param sellAmount: token amount to sell in base unit, default is 1e18
    :return: eth/bnb price per token for the specified amount to sell
    """

    if curr_network == "bsc" or curr_network == "bsc-fork":
        endpoint = "https://bsc.api.0x.org/"
        buyToken = "WBNB"
    elif curr_network == "eth":
        endpoint = "https://api.0x.org/"
        buyToken = "WETH"
    else:
        raise ValueError("Unrecognized network")

    params = (
        "swap/v1/quote?buyToken="
        + buyToken
        + "&sellToken="
        + token
        + "&sellAmount="
        + str(sellAmount)
    )
    r = requests.get(endpoint + params)
    data = r.json()

    if not data.get("guaranteedPrice"):
        console.log(data)
        raise ValueError("Price could not be fetched")

    return data["guaranteedPrice"]


def token_data(key: str, tend: bool) -> (str, str):
    """
    returns the yield token symbol and address for the strategy

    :param key: strategy key e.g. native.sushiWbtcEth
    :param tend: whether or not this is token data for a tend (as opposed to a harvest)
    :return: tuple of token symbol and address
    """

    token = get_symbol(key, tend)
    if not token:
        console.log("token for strategy", key, "not found")
        return (None, None)

    token_address = get_address(token)
    if not type(token_address) == str:
        console.log("address for token", token, "not found")

    return (token, token_address)


def calc_profit(earnings: int, token_address: str, token: str) -> int:
    """
    calculate profit in eth/bnb for the selected token and earned amount

    :param earnings: amount of token that has been earned
    :param token_address: address of earned token
    :param token: token symbol
    :return: amount of eth/bnb that could be earned from selling the specified amount
    """

    if earnings > 0:
        price = get_price(token_address, sellAmount=earnings)
    else:
        price = get_price(token_address)

    token_contract = interface.IERC20(token_address)
    decimals = token_contract.decimals()
    eth_earnings = earnings / (10 ** decimals) * float(price)

    if curr_network == "bsc":
        console.log(
            "harvest token:",
            token,
            "earnings:",
            earnings,
            "price in bnb:",
            price,
            "bnb profit:",
            eth_earnings,
        )
    elif curr_network == "eth":
        console.log(
            "harvest token:",
            token,
            "earnings:",
            earnings,
            "price in eth:",
            price,
            "eth earnings:",
            eth_earnings,
        )

    return eth_earnings


def get_symbol(key: str, tend=False) -> str:
    """
    get the symbol of the yield token for the selected strategy

    :param key: strategy key
    :param tend: whether this is for a tend (as opposed to a harvest)
    :return: token symbol
    """

    if curr_network == "eth":
        if is_crv_strategy(key):
            return curve_registry.symbol
        if is_badger_strategy(key):
            return badger_registry.symbol
        if is_sushi_strategy(key, tend):
            return sushi_registry.symbol
        if is_xsushi_strategy(key):
            return sushi_registry.symbol_xsushi
        if is_digg_strategy(key):
            return digg_registry.symbol
        if is_farm_strategy(key):
            return harvest_registry.symbol
    elif curr_network == "bsc":
        if is_pancake_strategy(key):
            return bsc_registry.pancake.symbol


def get_address(token: str) -> str:
    """
    get the address of the token

    :param token: token symbol
    :return: token address
    """

    if curr_network == "eth":
        if token == "XSUSHI":
            return eth_registry.tokens.xSushi
        return eth_registry.tokens[token.lower()]
    elif curr_network == "bsc":
        if token == "Cake":
            return bsc_registry.pancake.cake
        else:
            return bsc_registry.tokens[token.lower()]


def is_farm_strategy(key: str) -> bool:
    return key in ["harvest.renCrv"]


def is_crv_strategy(key: str) -> bool:
    return key in ["native.renCrv", "native.sbtcCrv", "native.tbtcCrv"]


def is_badger_strategy(key: str) -> bool:
    return key in ["native.uniBadgerWbtc", "native.sushiBadgerWbtc"]


def is_digg_strategy(key: str) -> bool:
    return key in ["native.uniDiggWbtc", "native.sushiDiggWbtc"]


def is_sushi_strategy(key: str, tend=False) -> bool:
    return key in ["native.sushiWbtcEth", "native.sushiDiggWbtc"] and tend


def is_xsushi_strategy(key: str) -> bool:
    return key in ["native.sushiWbtcEth"]


def is_pancake_strategy(key: str) -> bool:
    return key in ["native.pancakeBnbBtcb", "native.bBadgerBtcb", "native.bDiggBtcb"]
