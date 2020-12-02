from helpers.time_utils import daysToSeconds
import os
import json
from scripts.systems.badger_system import connect_badger
import warnings
from tabulate import tabulate
from brownie import *
from helpers.registry import registry

warnings.simplefilter("ignore")
# keeper = accounts.load("keeper")


def main():
    fileName = "deploy-" + str(chain.id) + ".json"
    badger = connect_badger(fileName)
    token = badger.token

    table = []

    hunt = badger.badgerHunt
    table.append(['nextEpochStart', hunt.getNextEpochStart()])
    table.append(['timeTillNextEpoch', hunt.getNextEpochStart() - chain.time()])
    table.append(['currentEpoch', hunt.getCurrentEpoch()])
    table.append(['epochDuration', hunt.epochDuration()])
    table.append(['rewardReductionPerEpoch', hunt.rewardReductionPerEpoch()])
    table.append(['finalEpoch', hunt.finalEpoch()])
    table.append(['claimsStartTime', hunt.getClaimsStartTime()])
    table.append(['gracePeriodEnd', hunt.getGracePeriodEnd()])
    table.append(['currentEpoch', hunt.getCurrentEpoch()])
    table.append(['currentRewardsRate', hunt.getCurrentRewardsRate()])
    table.append(['nextEpochRewardsRate', hunt.getNextEpochRewardsRate()])

    table.append(['---------------', "--------------------"])
    table.append(['nextEpochStart', hunt.getNextEpochStart() / 60 / 60])
    print(tabulate(table, headers=["metric", "value"]))
