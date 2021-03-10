from brownie import *
import math
import json
from rich.console import Console
from assistant.subgraph.client import (
    fetch_wallet_balances,
)
from collections import Counter, OrderedDict
from assistant.rewards.rewards_utils import (
    combine_balances,
    calculate_sett_balances
)
from assistant.badger_api.prices import (
    fetch_token_price,
    fetch_sett_ppfs,
)

console = Console()
digg_token = "0x798D1bE841a82a273720CE31c822C61a67a601C3"
badger_token = "0x3472A5A71965499acd81997a54BBA8D852C6E53d"
MAX_MULTIPLIER = 3


def convert_balances_to_usd(sett, name, settType, balances):
    price = fetch_token_price(sett.token().lower())
    ppfs = fetch_sett_ppfs(sett.token().lower())
    price_ratio = 1
    # Weight native lp by half
    if "uni" in name or "sushi" in name and settType == "badger" or settType == "digg":
        price_ratio = 0.5

    for account, bBalance in balances.items():
        balances[account] = (price * bBalance * ppfs) / 1e18 * price_ratio

    return balances


def calc_cumulative(l):
    result = [None] * len(l)
    cumulative = 0
    for idx, val in enumerate(l):
        cumulative += val
        result[idx] = cumulative
    return result

def calc_boost(percentages):
    return [MAX_MULTIPLIER - (p * (MAX_MULTIPLIER - 1)) for p in percentages ]


def calc_stake_ratio(address, diggSetts, badgerSetts, nonNativeSetts):
    diggBalance = diggSetts.get(address, 0)
    badgerBalance = badgerSetts.get(address, 0)
    nonNativeBalance = nonNativeSetts.get(address, 0)
    console.log
    if nonNativeBalance == 0:
        return 0
    else:
        return (diggBalance + badgerBalance) / nonNativeBalance

def calc_address_balances(address, diggSetts, badgerSetts, nonNativeSetts):
    diggBalance = 0
    badgerBalance = 0
    nonNativeBalance = 0
    for name, balances in diggSetts.items():
        diggBalance += balances.get(address, 0)
    for name, balances in badgerSetts.items():
        badgerBalance += balances.get(address, 0)
    for name, balances in nonNativeSetts.items():
        nonNativeBalance += balances.get(address, 0)

    return (diggBalance, badgerBalance, nonNativeBalance)


def get_balance_data(badger, currentBlock):
    allSetts = badger.sett_system.vaults
    diggSetts = {}
    badgerSetts = {}
    nonNativeSetts = {}
    for name, sett in allSetts.items():
        balances = calculate_sett_balances(badger, name, sett, currentBlock)
        if name in ["native.uniDiggWbtc", "native.sushiDiggWbtc", "native.digg"]:
            balances = convert_balances_to_usd(sett, name, "digg", balances)
            diggSetts = combine_balances([diggSetts, balances])
        elif name in [
            "native.badger",
            "native.uniBadgerWbtc",
            "native.sushiBadgerWbtc",
        ]:
            balances = convert_balances_to_usd(sett, name, "badger", balances)
            badgerSetts = combine_balances([badgerSetts, balances])
        else:
            balances = convert_balances_to_usd(sett, name, "nonnative", balances)
            nonNativeSetts = combine_balances([nonNativeSetts, balances])

    badger_wallet_balances, digg_wallet_balances = fetch_wallet_balances(
        fetch_token_price(badger_token.lower()),
        fetch_token_price(digg_token.lower()),
        badger.digg,
    )

    badgerSetts = combine_balances([badgerSetts, badger_wallet_balances])
    diggSetts = combine_balances([diggSetts, digg_wallet_balances])

    allAddresses = list(
        set(diggSetts.keys()).union(
            set(badgerSetts.keys()).union(set(nonNativeSetts.keys()))
        )
    )
    # Need to get rid of the whale addresses
    stakeRatiosList = [
        calc_stake_ratio(addr, diggSetts, badgerSetts, nonNativeSetts)
        for addr in allAddresses
    ]
    stakeRatios = dict(zip(allAddresses, stakeRatiosList))
    stakeRatios = OrderedDict(
        sorted(stakeRatios.items(), key=lambda t: t[1]), reverse=True
    )
    console.log(stakeRatios)
    sortedNonNative = OrderedDict(
        sorted(nonNativeSetts.items(), key=lambda t: stakeRatios[t[0]], reverse=True)
    )
    nonNativeTotal = sum(sortedNonNative.values())
    for addr, nonNativeBalance in sortedNonNative.items():
        percentage = nonNativeBalance / nonNativeTotal
        sortedNonNative[addr] = percentage
    cumulativePercentages = dict(
        zip(sortedNonNative.keys(), calc_cumulative(sortedNonNative.values()))
    )
    badgerBoost = dict(
        zip(cumulativePercentages.keys(), calc_boost(cumulativePercentages.values()))
    )
    console.log(badgerBoost)
    console.log(len(badgerBoost))
    with open('badger-boost.json', 'w') as fp:
        json.dump(badgerBoost, fp)

    return badgerBoost

