from brownie import *
import json
import csv
from rich.console import Console
from assistant.subgraph.client import fetch_wallet_balances
from helpers.constants import BADGER, DIGG, SETT_BOOST_RATIOS, MAX_BOOST
from helpers.digg_utils import diggUtils

from collections import OrderedDict
from assistant.rewards.rewards_utils import combine_balances, calculate_sett_balances
from assistant.badger_api.prices import fetch_token_prices
from assistant.badger_api.account import fetch_claimable_balances

from assistant.rewards.aws_utils import upload_nfts
from assistant.rewards.classes.UserBalance import UserBalance, UserBalances
from assistant.rewards.nfts import calc_nft_multipliers

boostInfo = {}
prices = fetch_token_prices()
console = Console()

boostInfo = {}


def convert_balances_to_usd(sett, name, userBalances):
    tokenAddress = sett.address
    price = prices[tokenAddress]
    decimals = interface.IERC20(tokenAddress).decimals()
    price_ratio = SETT_BOOST_RATIOS[name]

    for user in userBalances:
        user.balance = (price_ratio * price * user.balance) / (pow(10, decimals))

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
        boost = MAX_BOOST - (p * (MAX_BOOST - 1))
        if boost < 1:
            boost = 1
        boosts.append(boost)
    return boosts


def calc_stake_ratio(address, diggSetts, badgerSetts, nonNativeSetts, nftBoosts):
    nftBoost = nftBoosts.get(address, {"multiplier": 1})["multiplier"]
    diggBalance = getattr(diggSetts[address], "balance", 0)
    badgerBalance = getattr(badgerSetts[address], "balance", 0)
    nonNativeBalance = getattr(nonNativeSetts[address], "balance", 0)
    if nonNativeBalance == 0:
        return 0

    return (nftBoost * diggBalance + badgerBalance) / nonNativeBalance


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


def chunk(l, n):
    n = max(1, n)
    return (l[i : i + n] for i in range(0, len(l), n))


def badger_boost(badger, currentBlock):

    console.log("Calculating boost ...")

    allSetts = badger.sett_system.vaults
    diggSetts = UserBalances()
    badgerSetts = UserBalances()
    nonNativeSetts = UserBalances()
    boostInfo = {}
    console.log("Calculating NFT Multipliers ...")
    nftMultipliers = calc_nft_multipliers(currentBlock)

    for name, sett in allSetts.items():
        if name in ["experimental.digg"]:
            continue
        balances = calculate_sett_balances(badger, name, currentBlock)
        balances = convert_balances_to_usd(sett, name, balances)
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

    sharesPerFragment = badger.digg.logic.UFragments._sharesPerFragment()
    badger_wallet_balances, digg_wallet_balances, _ = fetch_wallet_balances(
        sharesPerFragment, currentBlock
    )
    console.log("Fetching Claimable Balances...")
    nonNativeAddresses = list(nonNativeSetts.userBalances.keys())

    console.log(len(nonNativeAddresses))
    chunked_addresses = chunk(nonNativeAddresses, 100)
    claimableData = {}
    for addr_list in chunked_addresses:
        console.log("{} claims fetched".format(len(addr_list)))
        claimableData = {**claimableData, **fetch_claimable_balances(addr_list)}

    console.log(len(claimableData))

    for addr, claimableBalances in claimableData.items():
        claimableBadger = 0
        claimableDigg = 0

        for cb in claimableBalances:
            if cb["address"] == BADGER:
                claimableBadger = cb["balance"] / 1e18
            if cb["address"] == DIGG:
                claimableDigg = diggUtils.sharesToFragments(cb["balance"]) / 1e9

        claimableBadger *= prices[BADGER]
        claimableDigg *= prices[DIGG]

        currentBadger = badger_wallet_balances.get(addr.lower(), 0)
        currentDigg = digg_wallet_balances.get(addr.lower(), 0)

        badger_wallet_balances[addr] = currentBadger + claimableBadger
        digg_wallet_balances[addr] = currentDigg + claimableDigg

    console.log(
        "{} Badger balances fetched, {} Digg balances fetched".format(
            len(badger_wallet_balances), len(digg_wallet_balances)
        )
    )
    badger_wallet_balances = UserBalances(
        [
            UserBalance(addr, bal * prices[BADGER], BADGER)
            for addr, bal in badger_wallet_balances.items()
        ]
    )

    digg_wallet_balances = UserBalances(
        [
            UserBalance(addr, bal * prices[DIGG], DIGG)
            for addr, bal in digg_wallet_balances.items()
        ]
    )

    badgerSetts = filter_dust(combine_balances([badgerSetts, badger_wallet_balances]))
    diggSetts = filter_dust(combine_balances([diggSetts, digg_wallet_balances]))
    allAddresses = calc_union_addresses(diggSetts, badgerSetts, nonNativeSetts)

    console.log("Non native Setts before filter {}".format(len(nonNativeSetts)))
    nonNativeSetts = filter_dust(nonNativeSetts)
    console.log("Non native Setts after filter {}".format(len(nonNativeSetts)))

    console.log("Filtered balances < $1")

    console.log(
        "{} addresses collected for boost calculation".format(len(allAddresses))
    )

    stakeRatiosList = [
        calc_stake_ratio(addr, diggSetts, badgerSetts, nonNativeSetts, nftMultipliers)
        for addr in allAddresses
    ]
    stakeRatios = dict(zip(allAddresses, stakeRatiosList))

    stakeRatios = OrderedDict(
        sorted(stakeRatios.items(), key=lambda t: t[1], reverse=True)
    )

    for addr in allAddresses:
        boostInfo[addr.lower()] = {
            "nativeBalance": 0,
            "nonNativeBalance": 0,
            "stakeRatio": 0,
        }

    for user in badgerSetts:
        boostInfo[user.address.lower()]["nativeBalance"] += user.balance

    for user in diggSetts:
        boostInfo[user.address.lower()]["nativeBalance"] += user.balance

    for user in nonNativeSetts:
        boostInfo[user.address.lower()]["nonNativeBalance"] += user.balance

    for addr, ratio in stakeRatios.items():
        boostInfo[addr.lower()]["stakeRatio"] = ratio

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
    for addr, boost in badgerBoost.items():
        # Users with no stake ratio have a boost of 1
        if stakeRatios[addr] == 0:
            badgerBoost[addr] = 1

    console.log(len(badgerBoost))

    with open("nft_scores.json", "w") as fp:
        json.dump(nftMultipliers, fp)

    upload_nfts(test=False)

    return badgerBoost, boostInfo
