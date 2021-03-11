from assistant.rewards.rewards_utils import calculate_sett_balances
from assistant.rewards.classes.RewardsList import RewardsList
from brownie import *
digg_token = "0x798D1bE841a82a273720CE31c822C61a67a601C3"


def calc_geyser_snapshot(badger, name, startBlock, endBlock, nextCycle):
    rewards = RewardsList(nextCycle, badger.badgerTree)
    sett = badger.getSett(name)
    geyser = badger.getGeyser(name)
    startTime = web3.eth.getBlock(startBlock)["timestamp"]
    endTime = web3.eth.getBlock(endBlock)["timestamp"]

    balances = calculate_sett_balances(badger, name, sett, endBlock)
    unlockSchedules = {}
    for token in geyser.getDistributionTokens():
        unlockSchedules = geyser.getUnlockSchedulesFor(token)
        if token == digg_token:
            pass
            # Add peg based rewards here
        tokenDistribution = int(
            get_distributed_for_token_at(token, endTime, unlockSchedules)
            - get_distributed_for_token_at(token, startTime, unlockSchedules)
        )
        rewardsUnit = sum(balances.values()) / tokenDistribution
        ## Distribute to users with rewards list
        for addr, balance in balances.items():
            #  Add badger boost here (for non native setts)
            rewards.increase_user_rewards(addr, token, balance * rewardsUnit)

    return rewards


def get_distributed_for_token_at(token, endTime, schedules):
    for index, schedule in enumerate(schedules):
        if endTime < schedule.startTime:
            toDistribute = 0
            console.log("\nSchedule {} for {} completed".format(index, name))
        else:
            rangeDuration = endTime - schedule.startTime
            toDistribute = min(
                schedule.initialTokensLocked,
                int(schedule.initalTokensLocked * rangeDuration // schedule.duration),
            )
        totalToDistribute += toDistribute

    return totalToDistribute
