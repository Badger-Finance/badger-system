from assistant.rewards.rewards_utils import calculate_sett_balances
from assistant.rewards.classes.RewardsList import RewardsList
from assistant.rewards.classes.RewardsLogger import rewardsLogger
from assistant.rewards.classes.Schedule import Schedule
from assistant.rewards.enums import Token
from helpers.time_utils import days, to_days, to_hours, to_utc_date
from dotmap import DotMap
from brownie import *
from rich.console import Console

console = Console()
digg = interface.IDigg(Token.digg.value)

nativeSetts = ["native.uniDiggWbtc", "native.sushiDiggWbtc"]
nonNativeSetts = [
    "native.renCrv",
    "native.sbtcCrv",
    "native.tbtcCrv",
    "native.sushiWbtcEth"
    "harvest.renCrv",
    "yearn.wbtc" 
]


def calc_geyser_snapshot(badger, name, startBlock, endBlock, nextCycle, boosts, diggAllocation):

    console.log("==== Processing rewards for {} ====".format(name))
    rewards = RewardsList(nextCycle, badger.badgerTree)
    geyser = badger.getGeyser(name)
    startTime = web3.eth.getBlock(startBlock)["timestamp"]
    endTime = web3.eth.getBlock(endBlock)["timestamp"]

    userBalances = calculate_sett_balances(badger, name, endBlock)
    # Get rid of blacklisted addresses
    # Only boost non-native setts
    if name in nonNativeSetts:
        for user in userBalances:
            boostAmount = boosts.get(user.address, 1)
            user.boost_balance(boostAmount)

    unlockSchedules = {}
    for token in geyser.getDistributionTokens():
        unlockSchedules = parse_schedules(geyser.getUnlockSchedulesFor(token))
        endDist = get_distributed_for_token_at(token, endTime, unlockSchedules, name)
        startDist = get_distributed_for_token_at(token, startTime, unlockSchedules, name)
        tokenDistribution = int(endDist) - int(startDist)

        rewardsLogger.add_total_token_dist(name, token, tokenDistribution)
        # Distribute to users with rewards list
        # Make sure there are tokens to distribute (some geysers only
        # distribute one token)
        if token == Token.digg.value:
            if name in nativeSetts:
                tokenDistribution = tokenDistribution * diggAllocation
            else:
                tokenDistribution = tokenDistribution * (1 - diggAllocation)

            console.log(
                "{} DIGG tokens distributed".format(
                    digg.sharesToFragments(tokenDistribution)/1e18)
            )

        else:
            console.log(
                "{} Badger tokens distributed".format(
                    tokenDistribution/1e18)
            )

        if tokenDistribution > 0:
            sumBalances = sum([b.balance for b in userBalances])
            rewardsUnit = tokenDistribution/sumBalances
            totalRewards = 0
            console.log(
                "Processing rewards for {} addresses".format(len(userBalances)))
            for user in userBalances:
                addr = web3.toChecksumAddress(user.address)
                token = web3.toChecksumAddress(token)
                rewardAmount = user.balance * rewardsUnit
                totalRewards += rewardAmount
                rewards.increase_user_rewards(addr, token, int(rewardAmount))
                rewardsLogger.add_user_token(
                    addr, name, token, int(rewardAmount))
            console.log("Token Distribution: {}\nRewards Released: {}".format(
                tokenDistribution/1e18,totalRewards/1e18
            ))
            console.log(abs(tokenDistribution - totalRewards))

    return rewards


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
                int(
                    schedule.initialTokensLocked
                    * rangeDuration
                    // schedule.duration
                ),
            )
            if schedule.startTime <= endTime and schedule.endTime >= endTime:
                console.log("Tokens distributed by schedule {} at {} are {}% of total\n".format(
                    index,
                    to_utc_date(schedule.startTime),
                    (int(toDistribute)/int(schedule.initialTokensLocked)*100)
                ))

                console.log(
                    "Total duration of schedule elapsed is {} hours out of {} hours, or {}% of total duration.\n"
                    .format(
                        to_hours(rangeDuration),
                        to_hours(schedule.duration),
                        rangeDuration / schedule.duration * 100
                    )
                )
        totalToDistribute += toDistribute
    return totalToDistribute


def parse_schedules(schedules):
    return list(map(lambda s: Schedule(s[0], s[1], s[2], s[3]), schedules))
