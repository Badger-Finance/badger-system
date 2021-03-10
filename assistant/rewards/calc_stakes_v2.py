from assistant.rewards.rewards_utils import calculate_sett_balances
from assistant.rewards.classes.RewardsList import RewardsList

def calc_geyser_snapshot(badger, name, startBlock, endBlock):
    sett = badger.getSett(name)
    geyser = badger.getGeyser(name)
    startTime = web3.eth.getBlock(startBlock)["timestamp"]
    endTime = web3.eth.getBlock(endBlock)["timestamp"]

    balances = calculate_sett_balances(badger, name, sett, endBlock)
    unlockSchedules = {}
    for token in geyser.getDistributionTokens():
        totalToDistribute = 0
        unlockSchedules = geyser.getUnlockSchedulesFor(token)
        tokenDistribution = int(
            get_distributed_for_token_at(token, endTime, unlockSchedules)
            - get_distributed_for_token_at(token,startTime,unlockSchedules)
        )
        ## Distribute to users with rewards list


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
