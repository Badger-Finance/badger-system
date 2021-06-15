from brownie import *
import json
import csv
from rich.console import Console
from assistant.rewards.aws_utils import upload_nft_scores
from assistant.subgraph.client import fetch_wallet_balances
from helpers.constants import BADGER, DIGG
from helpers.digg_utils import diggUtils
from collections import OrderedDict
from assistant.rewards.rewards_utils import combine_balances, calculate_sett_balances
from assistant.badger_api.prices import (
    fetch_token_prices,
    fetch_ppfs,
)

from assistant.rewards.classes.UserBalance import UserBalance, UserBalances
from assistant.rewards.nfts import calc_nft_multipliers

boostInfo = {}
prices = fetch_token_prices()
console = Console()
MAX_MULTIPLIER = 3


badgerTree = Contract.from_explorer("0x660802Fc641b154aBA66a62137e71f331B6d787A")


def add_boost_info(balances, name):
    for user in balances:
        if user.address not in boostInfo:
            boostInfo[user.address] = {}
        boostInfo[user.address][name] = user.balance


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
        user.balance = price_ratio * (price * user.balance) / (pow(10, decimals))

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


def calc_stake_ratio(address, diggSetts, badgerSetts, nonNativeSetts, nftBoosts):
    nftBoost = nftBoosts.get(address, {"multiplier": 1})["multiplier"]
    diggBalance = getattr(diggSetts[address], "balance", 0)
    badgerBalance = getattr(badgerSetts[address], "balance", 0)
    nonNativeBalance = getattr(nonNativeSetts[address], "balance", 0)
    if nonNativeBalance == 0:
        return 0

    if nonNativeBalance > 0:
        if address not in boostInfo:
            boostInfo[address] = {}
        boostInfo[address]["nativeBalance"] = diggBalance + badgerBalance
        boostInfo[address]["nonNativeBalance"] = nonNativeBalance
        boostInfo[address]["nftBoost"] = nftBoost

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


def badger_boost(badger, pastRewards, currentBlock):

    console.log("Calculating boost ...")
    console.log(len(pastRewards["claims"]))

    allSetts = badger.sett_system.vaults
    diggSetts = UserBalances()
    badgerSetts = UserBalances()
    nonNativeSetts = UserBalances()
    for name, sett in allSetts.items():
        balances = calculate_sett_balances(badger, name, currentBlock)
        balances = convert_balances_to_usd(sett, balances)
        add_boost_info(balances, name)

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
    for addr, claimData in pastRewards["claims"].items():
        tokens = claimData["tokens"]
        amounts = claimData["cumulativeAmounts"]

        claimableBadger = 0
        claimableDigg = 0

        tokens, amounts = badgerTree.getClaimableFor(addr, tokens, amounts)
        if BADGER in tokens:
            badgerAmount = float(amounts[tokens.index(BADGER)])
            claimableBadger = float(badgerAmount) / 1e18
        if DIGG in tokens:
            diggAmount = float(amounts[tokens.index(DIGG)])
            claimableDigg = diggUtils.sharesToFragments(diggAmount) / 1e9

        claimableBadger *= prices[BADGER]
        claimableDigg *= prices[DIGG]

        console.log("{} {} {}".format(addr, claimableBadger, claimableDigg))

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
        [UserBalance(addr, bal, BADGER) for addr, bal in badger_wallet_balances.items()]
    )
    add_boost_info(badger_wallet_balances, "Badger")

    digg_wallet_balances = UserBalances(
        [UserBalance(addr, bal, DIGG) for addr, bal in digg_wallet_balances.items()]
    )

    add_boost_info(digg_wallet_balances, "Digg")

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

    console.log("Calculating NFT Multipliers ...")

    nftMultipliers = calc_nft_multipliers(currentBlock)

    stakeRatiosList = [
        calc_stake_ratio(addr, diggSetts, badgerSetts, nonNativeSetts, nftMultipliers)
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
    for addr, boost in badgerBoost.items():
        # Users with no stake ratio have a boost of 1
        if stakeRatios[addr] == 0:
            badgerBoost[addr] = 1

        boostInfo[addr]["boost"] = boost

    with open("logs/boostInfo-{}.csv".format(currentBlock), "w") as fp:
        writer = csv.writer(fp, delimiter=",")
        writer.writerow(
            ["address", "nativeBalance", "nonNativeBalance", "boost", "nftBoost"]
        )
        for addr, data in boostInfo.items():
            writer.writerow(
                [
                    addr,
                    data.get("nativeBalance", 0),
                    data.get("nonNativeBalance", 0),
                    data.get("boost", 0),
                    data.get("nftBoost", 0),
                ]
            )

    return badgerBoost, stakeRatios, nftMultipliers
