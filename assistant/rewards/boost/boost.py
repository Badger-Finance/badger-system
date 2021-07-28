from brownie import *
from rich.console import Console
import json
from helpers.constants import (
    BADGER,
    DIGG,
    SETT_BOOST_RATIOS,
    MAX_BOOST,
    STAKE_RATIO_RANGES,
)
from collections import OrderedDict
from assistant.rewards.rewards_utils import combine_balances
from scripts.systems.badger_system import BadgerSystem
from tabulate import tabulate

from assistant.rewards.classes.UserBalance import UserBalance, UserBalances
from assistant.rewards.boost.utils import (
    calc_union_addresses,
    calc_boost_data,
)

console = Console()


def calc_stake_ratio(
    address: str, nativeSetts: UserBalances, nonNativeSetts: UserBalances
):
    """
    Calculate the stake ratio for an address
    :param address: address to find stake ratio for
    :param nativeSetts: native balances
    :param nonNativeSetts: non native balances
    """
    nativeBalance = getattr(nativeSetts[address], "balance", 0)
    nonNativeBalance = getattr(nonNativeSetts[address], "balance", 0)
    if nonNativeBalance == 0 or nativeBalance == 0:
        stakeRatio = 0
    else:
        console.log("Non zero stakeRatio :)")
        stakeRatio = (nativeBalance) / nonNativeBalance
    return stakeRatio


def badger_boost(badger: BadgerSystem, currentBlock: int):
    """
    Calculate badger boost multipliers based on stake ratios
    :param badger: badger system
    :param currentBlock: block to calculate boost at
    """
    console.log("Calculating boost at block {} ...".format(currentBlock))
    nativeSetts, nonNativeSetts = calc_boost_data(badger, currentBlock)
    allAddresses = calc_union_addresses(nativeSetts, nonNativeSetts)
    console.log("{} addresses fetched".format(len(allAddresses)))
    console.log(nativeSetts)
    badgerBoost = {}
    boostInfo = {}
    boostData = {}

    stakeRatiosList = [
        calc_stake_ratio(addr, nativeSetts, nonNativeSetts) for addr in allAddresses
    ]

    stakeRatios = dict(zip(allAddresses, stakeRatiosList))
    stakeRatios = OrderedDict(
        sorted(stakeRatios.items(), key=lambda t: t[1], reverse=True)
    )

    boostInfo = {}
    for addr in allAddresses:
        boostInfo[addr] = {"nativeBalance": 0, "nonNativeBalance": 0, "stakeRatio": 0}
    for user in nativeSetts:
        boostInfo[user.address.lower()]["nativeBalance"] = user.balance

    for user in nonNativeSetts:
        boostInfo[user.address.lower()]["nonNativeBalance"] = user.balance

    for addr, ratio in stakeRatios.items():
        boostInfo[addr.lower()]["stakeRatio"] = ratio

    stakeData = {}
    console.log(STAKE_RATIO_RANGES)
    for addr, stakeRatio in stakeRatios.items():
        if stakeRatio == 0:
            badgerBoost[addr] = 1
        else:

            userBoost = 1
            userStakeRange = 0
            for stakeRange, multiplier in STAKE_RATIO_RANGES:
                if stakeRatio > stakeRange:
                    userBoost = multiplier
                    userStakeRange = stakeRange

            stakeData[userStakeRange] = stakeData.get(userStakeRange, 0) + 1
            badgerBoost[addr] = userBoost

    for addr, boost in badgerBoost.items():
        boostMetaData = boostInfo.get(addr, {})
        boostData[addr] = {
            "boost": boost,
            "nativeBalance": boostMetaData.get("nativeBalance", 0),
            "nonNativeBalance": boostMetaData.get("nonNativeBalance", 0),
            "stakeRatio": boostMetaData.get("stakeRatio", 0),
        }

    with open("badger-boosts.json", "w") as fp:
        json.dump(boostData, fp)

    console.log(len(badgerBoost))
    print(
        tabulate(
            [[rng, amount] for rng, amount in stakeData.items()],
            headers=["range", "amount of users"],
        )
    )

    return badgerBoost, boostInfo
