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
    test = True
    # if rpc.is_active():
    #     sender = accounts[0]
    # else:
    #     priv = os.environ.get('VAULT_KEEPER_PRIV')
    #     sender = accounts.add(priv) if priv else accounts.load(input('brownie account: '))
    fileName = "deploy-" + str(chain.id) + ".json"
    badger = connect_badger(fileName)
    token = badger.token

    table = []
    contracts = {}
    tokens = {}
    for key, contract in badger.sett_system.vaults.items():
        contracts["Sett " + key] = contract

    contracts["badgerTree"] = badger.badgerTree
    contracts["badgerHunt"] = badger.badgerHunt
    contracts["rewardsEscrow"] = badger.rewardsEscrow

    tokens["badger"] = interface.IERC20(badger.token.address)
    tokens["farm"] = interface.IERC20(registry.harvest.farmToken)

    for contractName, contract in contracts.items():
        data = []
        data.append(contractName)
        # Tokens: badger / farm
        for tokenName, token in tokens.items():
            data.append(token.balanceOf(contract) / 1e18)

        table.append(data)

    print(tabulate(table, headers=["contract", "badger", "farm"]))

    # if vaults:
    #     print("poking these vaults:", vaults)
    #     keeper.earn(vaults, {"from": sender, "gas_limit": 2_500_000})
    # else:
    #     print("no vaults to poke, exiting")

