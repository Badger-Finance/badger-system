from assistant.rewards.rewards_utils import calculate_sett_balances
from assistant.rewards.classes.RewardsList import RewardsList
from assistant.rewards.classes.RewardsLog import rewardsLog
from assistant.rewards.classes.Schedule import Schedule
from helpers.time_utils import to_days, to_hours, to_utc_date
from helpers.constants import NON_NATIVE_SETTS, NATIVE_DIGG_SETTS, DIGG
from dotmap import DotMap
from brownie import *
from rich.console import Console

console = Console()


def calc_snapshot(
    badger, name, startBlock, endBlock, nextCycle, boosts, diggAllocation
):
    digg = interface.IDigg(DIGG)

    console.log("==== Processing rewards for {} at {} ====".format(name, endBlock))

    rewards = RewardsList(nextCycle, badger.badgerTree)

    sett = badger.getSett(name)
    startTime = web3.eth.getBlock(startBlock)["timestamp"]

    endTime = web3.eth.getBlock(endBlock)["timestamp"]

    userBalances = calculate_sett_balances(badger, name, endBlock)

    apyBoosts = {}
    if name in NON_NATIVE_SETTS:
        console.log(
            "{} users out of {} boosted in {}".format(
                len(boosts), len(userBalances), name
            )
        )
        preBoost = {}
        for user in userBalances:
            preBoost[user.address] = userBalances.percentage_of_total(user.address)

        for user in userBalances:
            boostAmount = boosts.get(user.address, 1)
            user.boost_balance(boostAmount)

        for user in userBalances:
            postBoost = userBalances.percentage_of_total(user.address)
            apyBoosts[user.address] = postBoost / preBoost[user.address]

    schedulesByToken = parse_schedules(
        badger.rewardsLogger.getAllUnlockSchedulesFor(sett)
    )

    for token, schedules in schedulesByToken.items():
        endDist = get_distributed_for_token_at(token, endTime, schedules, name)
        startDist = get_distributed_for_token_at(token, startTime, schedules, name)
        tokenDistribution = int(endDist) - int(startDist)
        # Distribute to users with rewards list
        # Make sure there are tokens to distribute (some geysers only
        # distribute one token)
        if token == DIGG:

            # if name in NATIVE_DIGG_SETTS:
            #    tokenDistribution = tokenDistribution * diggAllocation
            # else:
            #    tokenDistribution = tokenDistribution * (1 - diggAllocation)

            console.log(
                "{} DIGG tokens distributed".format(
                    digg.sharesToFragments(tokenDistribution) / 1e18
                )
            )
        elif token == "0x20c36f062a31865bED8a5B1e512D9a1A20AA333A":
            console.log("{} DFD tokens distributed".format(tokenDistribution / 1e18))
        else:
            badgerAmount = tokenDistribution / 1e18
            rewardsLog.add_total_token_dist(name, token, badgerAmount)
            console.log("{} Badger tokens distributed".format(badgerAmount))

        if tokenDistribution > 0:
            console.print(len(userBalances))
            sumBalances = sum([b.balance for b in userBalances])
            rewardsUnit = tokenDistribution / sumBalances
            totalRewards = 0
            console.log("Processing rewards for {} addresses".format(len(userBalances)))
            for user in userBalances:
                addr = web3.toChecksumAddress(user.address)
                token = web3.toChecksumAddress(token)
                rewardAmount = user.balance * rewardsUnit
                totalRewards += rewardAmount
                rewards.increase_user_rewards(addr, token, int(rewardAmount))
                rewardsLog.add_user_token(addr, name, token, int(rewardAmount))

            console.log(
                "Token Distribution: {}\nRewards Released: {}".format(
                    tokenDistribution / 1e18, totalRewards / 1e18
                )
            )
            console.log("Diff {}".format((abs(tokenDistribution - totalRewards))))

    return rewards, apyBoosts


def get_distributed_for_token_at(token, endTime, schedules, name):
    totalToDistribute = 0
    for index, schedule in enumerate(schedules):
        if endTime < schedule.startTime:
            toDistribute = 0
            console.log("\nSchedule {} for {} completed\n".format(index, name))
        else:
            rangeDuration = endTime - schedule.startTime
            toDistribute = min(
                schedule.initialTokensLocked,
                int(schedule.initialTokensLocked * rangeDuration // schedule.duration),
            )
            if schedule.startTime <= endTime and schedule.endTime >= endTime:
                console.log(
                    "Tokens distributed by schedule {} at {} are {}% of total\n".format(
                        index,
                        to_utc_date(schedule.startTime),
                        (int(toDistribute) / int(schedule.initialTokensLocked) * 100),
                    )
                )

                console.log(
                    "Total duration of schedule elapsed is {} hours out of {} hours, or {}% of total duration.\n".format(
                        to_hours(rangeDuration),
                        to_hours(schedule.duration),
                        rangeDuration / schedule.duration * 100,
                    )
                )
        totalToDistribute += toDistribute
    return totalToDistribute


def parse_schedules(schedules):
    schedulesByToken = {}
    for s in schedules:
        schedule = Schedule(s[0], s[1], s[2], s[3], s[4], s[5])
        if schedule.token not in schedulesByToken:
            schedulesByToken[schedule.token] = []
        schedulesByToken[schedule.token].append(schedule)
    return schedulesByToken
