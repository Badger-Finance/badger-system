from brownie import *
from scripts.systems.badger_system import connect_badger
from tabulate import tabulate
from config.badger_config import badger_config


def main():
    badger = connect_badger(badger_config.prod_file)

    table = []

    hunt = badger.badgerHunt
    table.append(["nextEpochStart", hunt.getNextEpochStart()])
    table.append(["timeTillNextEpoch", hunt.getNextEpochStart() - chain.time()])
    table.append(["currentEpoch", hunt.getCurrentEpoch()])
    table.append(["epochDuration", hunt.epochDuration()])
    table.append(["rewardReductionPerEpoch", hunt.rewardReductionPerEpoch()])
    table.append(["finalEpoch", hunt.finalEpoch()])
    table.append(["claimsStartTime", hunt.getClaimsStartTime()])
    table.append(["gracePeriodEnd", hunt.getGracePeriodEnd()])
    table.append(["currentEpoch", hunt.getCurrentEpoch()])
    table.append(["currentRewardsRate", hunt.getCurrentRewardsRate()])
    table.append(["nextEpochRewardsRate", hunt.getNextEpochRewardsRate()])

    table.append(["---------------", "--------------------"])
    table.append(["nextEpochStart", hunt.getNextEpochStart() / 60 / 60])
    print(tabulate(table, headers=["metric", "value"]))
