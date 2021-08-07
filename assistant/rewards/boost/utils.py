from rich.console import Console
from assistant.rewards.classes.UserBalance import UserBalance, UserBalances
from collections import Counter
from brownie import *
from typing import Dict
from scripts.systems.badger_system import BadgerSystem
from assistant.rewards.snapshot.utils import chain_snapshot
from assistant.badger_api.prices import (
    fetch_token_prices,
)

console = Console()
prices = fetch_token_prices()


def calc_union_addresses(nativeSetts: Dict[str, int], nonNativeSetts: Dict[str, int]):
    """
    Combine addresses from native setts and non native setts
    :param nativeSetts: native setts
    :param nonNativeSetts: non native setts
    """
    nativeAddresses = list(nativeSetts.keys())
    nonNativeAddresses = list(nonNativeSetts.keys())
    return list(set(nativeAddresses + nonNativeAddresses))


def filter_dust(balances: Dict[str, int], dustAmount: int):
    """
    Filter out dust values from user balances
    :param balances: balances to filter
    :param dustAmount: dollar amount to filter by
    """
    return {addr: value for addr, value in balances.items() if value > dustAmount}


def convert_balances_to_usd(balances: UserBalances, sett: str):
    """
    Convert sett balance to usd and multiply by correct ratio
    :param balances: balances to convert to usd
    """
    price = prices[web3.toChecksumAddress(sett)]
    priceRatio = balances.settRatio
    settToken = interface.IERC20(sett)
    decimals = settToken.decimals()
    symbol = settToken.symbol() 
    console.log(symbol, decimals, price, priceRatio)
    usdBalances = {}
    for user in balances:
        usdBalances[user.address] = priceRatio * price * user.balance / pow(10, decimals)

    return usdBalances, balances.settType


def calc_boost_data(badger: BadgerSystem, block: int):
    """
    Calculate boost data required for boost calculation
    :param badger: badger system
    :param block: block to collect the boost data from
    """
    chains = ["eth", "bsc"]
    ## Figure out how to map blocks, maybe  time -> block per chain

    native = {}
    nonNative = {}

    for chain in chains:
        snapshot = chain_snapshot(badger, chain, block)
        console.log("Converting balances to USD")
        for sett, balances in snapshot.items():
            balances, settType = convert_balances_to_usd(balances, sett)
            if settType == "native":
                native = {**native, **balances}
            elif settType == "nonNative":
                nonNative = {**nonNative, **balances}

    native = filter_dust(native, 1)
    nonNative = filter_dust(nonNative, 1)
    return native, nonNative
