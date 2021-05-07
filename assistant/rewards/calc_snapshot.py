from assistant.rewards.rewards_utils import calculate_sett_balances
from assistant.rewards.classes.RewardsList import RewardsList
from assistant.rewards.classes.RewardsLog import rewardsLog
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


def calc_snapshot(badger, name, startBlock, endBlock, nextCycle, boosts, diggAllocation):

    console.log("==== Processing rewards for {} ====".format(name))
    rewards = RewardsList(nextCycle, badger.badgerTree)
    sett = badger.getSett(name)
    startTime = web3.eth.getBlock(startBlock)["timestamp"]
    endTime = web3.eth.getBlock(endBlock)["timestamp"]

    userBalances = calculate_sett_balances(badger, name, endBlock)
    # Boost all setts with snapshot
    for user in userBalances:
        addr = web3.toChecksumAddress(user.address)
        boostAmount = boosts.get(addr,1)
        user.boost_balance(boostAmount)

    schedulesByToken = parse_schedules(badger.rewardsLogger.getAllUnlockSchedulesFor(sett))
    console.log(schedulesByToken)
    for token,schedules in schedulesByToken.items():
        console.log(token)
        console.log(schedules)
        endDist = get_distributed_for_token_at(token, endTime, schedules, name)
        startDist = get_distributed_for_token_at(token, startTime, schedules, name)
        tokenDistribution = int(endDist) - int(startDist)
        rewardsLog.add_total_token_dist(name, token, tokenDistribution)
        # Distribute to users with rewards list
        # Make sure there are tokens to distribute (some geysers only
        # distribute one token)
        if token == Token.digg.value:

            #if name in nativeSetts:
            #    tokenDistribution = tokenDistribution * diggAllocation
            #else:
            #    tokenDistribution = tokenDistribution * (1 - diggAllocation)

            console.log(
                "{} DIGG tokens distributed".format(
                    digg.sharesToFragments(tokenDistribution)/1e18)
            )
        elif token == "0x20c36f062a31865bED8a5B1e512D9a1A20AA333A":
            console.log(
                "{} DFD tokens distributed".format(
                    tokenDistribution/1e18)
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
                rewardsLog.add_user_token(
                    addr, name, token, int(rewardAmount))

            console.log("Token Distribution: {}\nRewards Released: {}".format(
                tokenDistribution/1e18,totalRewards/1e18
            ))
            console.log("Diff {}".format((abs(tokenDistribution - totalRewards))))

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
    schedulesByToken = {}
    for s in schedules:
        schedule = Schedule(s[0],s[1],s[2],s[3],s[4],s[5])
        if schedule.token not in schedulesByToken:
            schedulesByToken[schedule.token] = []
        schedulesByToken[schedule.token].append(schedule)
    return schedulesByToken
