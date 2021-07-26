from assistant.rewards.classes.RewardsList import RewardsList
from assistant.rewards.classes.RewardsLog import rewardsLog
from assistant.rewards.classes.Schedule import Schedule
from helpers.time_utils import to_days, to_hours, to_utc_date
from helpers.digg_utils import diggUtils
from helpers.constants import (
    NON_NATIVE_SETTS,
    NATIVE_DIGG_SETTS,
    DIGG,
    BADGER_TREE,
    DFD,
)
from brownie import *
from rich.console import Console

console = Console()


def calc_rewards(badger: BadgerSystem, sett: str, balances: UserBalances, startBlock: int, endBlock: int, chain: str, boost):
    """
    Calculate rewards for a sett on any chain between a cycle
    :param badger: badger system
    :param sett: sett to calculate rewards for
    :param balances: balances to calculate rewards with
    :param startBlock: start block of cycle
    :param endBlock: end block of cycle
    :chain: chain to calculate rewards on
    :boost: boost multipliers for each chain
    """
    
    pass

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
