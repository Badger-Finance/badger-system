from brownie import *
import json
from rich.console import Console
from assistant.rewards.aws_utils import upload_boosts
from assistant.subgraph.client import fetch_wallet_balances
from helpers.constants import BADGER, DIGG
from collections import OrderedDict
from assistant.rewards.rewards_utils import combine_balances, calculate_sett_balances
from assistant.badger_api.prices import (
    fetch_token_prices,
    fetch_ppfs,
)

from assistant.rewards.classes.UserBalance import UserBalance, UserBalances

prices = fetch_token_prices()
console = Console()
MAX_MULTIPLIER = 3


def convert_balances_to_usd(sett, userBalances):
    tokenAddress = sett.address
    price = prices[tokenAddress]
    decimals = interface.IERC20(tokenAddress).decimals()

    price_ratio = 1
    # Weight native lp by half

    for user in userBalances:
        if user.type[0] == "halfLP":
            price_ratio = 0.5
        else:
            price_ratio = 1
        user.balance = (price * user.balance) / (pow(10, decimals) * price_ratio)

    return userBalances


def calc_cumulative(l):
    result = [None] * len(l)
    cumulative = 0
    for idx, val in enumerate(l):
        cumulative += val
        result[idx] = cumulative
    return result


def calc_boost(percentages):
    boosts = []
    for p in percentages:
        boost = MAX_MULTIPLIER - (p * (MAX_MULTIPLIER - 1))
        if boost < 1:
            boost = 1
        boosts.append(boost)
    return boosts


def calc_stake_ratio(address, diggSetts, badgerSetts, nonNativeSetts):
    diggBalance = getattr(diggSetts[address], "balance", 0)
    badgerBalance = getattr(badgerSetts[address], "balance", 0)
    nonNativeBalance = getattr(nonNativeSetts[address], "balance", 0)
    if nonNativeBalance == 0:
        return 0
    return (diggBalance + badgerBalance) / nonNativeBalance


def calc_union_addresses(diggSetts, badgerSetts, nonNativeSetts):
    return set.union(
        *[
            {user.address for user in diggSetts},
            {user.address for user in badgerSetts},
            {user.address for user in nonNativeSetts},
        ]
    )


def filter_dust(balances):
    return UserBalances(list(filter(lambda user: user.balance > 1, balances)))


def badger_boost(badger, currentBlock):
    console.log("Calculating boost ...")
    allSetts = badger.sett_system.vaults
    diggSetts = UserBalances()
    badgerSetts = UserBalances()
    nonNativeSetts = UserBalances()
    for name, sett in allSetts.items():
        if name in ["experimental.digg"]:
            continue
        balances = calculate_sett_balances(badger, name, currentBlock)
        balances = convert_balances_to_usd(sett, balances)
        if name in ["native.uniDiggWbtc", "native.sushiDiggWbtc", "native.digg"]:
            diggSetts = combine_balances([diggSetts, balances])
        elif name in [
            "native.badger",
            "native.uniBadgerWbtc",
            "native.sushiBadgerWbtc",
        ]:
            badgerSetts = combine_balances([badgerSetts, balances])
        else:
            nonNativeSetts = combine_balances([nonNativeSetts, balances])

    badger_wallet_balances, digg_wallet_balances = fetch_wallet_balances(
        prices[BADGER], prices[DIGG], badger.digg, currentBlock
    )

    console.log(
        "{} Badger balances fetched, {} Digg balances fetched".format(
            len(badger_wallet_balances), len(digg_wallet_balances)
        )
    )
    badger_wallet_balances = UserBalances(
        [UserBalance(addr, bal, BADGER) for addr, bal in badger_wallet_balances.items()]
    )

    digg_wallet_balances = UserBalances(
        [UserBalance(addr, bal, DIGG) for addr, bal in digg_wallet_balances.items()]
    )
    badgerSetts = filter_dust(combine_balances([badgerSetts, badger_wallet_balances]))

    diggSetts = filter_dust(combine_balances([diggSetts, digg_wallet_balances]))

    console.log("Non native Setts before filter {}".format(len(nonNativeSetts)))
    nonNativeSetts = filter_dust(nonNativeSetts)
    console.log("Non native Setts after filter {}".format(len(nonNativeSetts)))

    console.log("Filtered balances < $1")

    allAddresses = calc_union_addresses(diggSetts, badgerSetts, nonNativeSetts)
    console.log(
        "{} addresses collected for boost calculation".format(len(allAddresses))
    )
    stakeRatiosList = [
        calc_stake_ratio(addr, diggSetts, badgerSetts, nonNativeSetts)
        for addr in allAddresses
    ]
    stakeRatios = dict(zip(allAddresses, stakeRatiosList))
    stakeRatios = OrderedDict(
        sorted(stakeRatios.items(), key=lambda t: t[1], reverse=True)
    )
    sortedNonNative = UserBalances(
        sorted(
            nonNativeSetts.userBalances.values(),
            key=lambda u: stakeRatios[u.address],
            reverse=True,
        )
    )
    nonNativeTotal = sortedNonNative.total_balance()
    percentageNonNative = {}
    for user in sortedNonNative:
        percentage = user.balance / nonNativeTotal
        percentageNonNative[user.address] = percentage

    cumulativePercentages = dict(
        zip(percentageNonNative.keys(), calc_cumulative(percentageNonNative.values()))
    )
    badgerBoost = dict(
        zip(cumulativePercentages.keys(), calc_boost(cumulativePercentages.values()))
    )
    console.log(len(badgerBoost))

    return badgerBoost
