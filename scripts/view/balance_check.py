from brownie import *
from config.badger_config import badger_config
from helpers.registry import registry
from scripts.systems.badger_system import connect_badger
from tabulate import tabulate
from helpers.utils import val


def main():
    fileName = badger_config.prod_json
    badger = connect_badger(fileName)

    token = badger.token

    table = []
    contracts = {}
    tokens = {}

    for key, contract in badger.sett_system.controllers.items():
        contracts["Controller " + key] = contract

    for key, contract in badger.sett_system.vaults.items():
        contracts["Sett " + key] = contract

    for key, contract in badger.sett_system.strategies.items():
        contracts["Strategy " + key] = contract

    for key, contract in badger.sett_system.geysers.items():
        contracts["Geyser " + key] = contract

    for key, contract in badger.sett_system.rewards.items():
        contracts["Rewards " + key] = contract

    contracts["badgerTree"] = badger.badgerTree
    contracts["badgerHunt"] = badger.badgerHunt
    contracts["rewardsEscrow"] = badger.rewardsEscrow
    contracts["teamVesting"] = badger.teamVesting
    contracts["daoBadgerTimelock"] = badger.daoBadgerTimelock
    contracts["deployer"] = badger.deployer

    tokens["badger"] = interface.IERC20(badger.token.address)
    tokens["farm"] = interface.IERC20(registry.harvest.farmToken)
    tokens["keep"] = interface.IERC20("0x85eee30c52b0b379b046fb0f85f4f3dc3009afec")

    total = 0

    print(badger.token.address)

    for contractName, contract in contracts.items():
        data = []
        data.append(contractName)
        # Tokens: badger / farm
        for tokenName, token in tokens.items():
            amount = token.balanceOf(contract)
            data.append(val(amount))
            total += amount

        table.append(data)

    table.append(["total", val(total), "-"])

    print(tabulate(table, headers=["contract", "badger", "farm", "keep"]))

    # if vaults:
    #     print("poking these vaults:", vaults)
    #     keeper.earn(vaults, {"from": sender, "gas_limit": 2_500_000})
    # else:
    #     print("no vaults to poke, exiting")

    table = []
    table.append(["beneficiary", badger.teamVesting.beneficiary()])
    table.append(["beneficiary", badger.daoBadgerTimelock.beneficiary()])
    print(tabulate(table, headers=["param", "value"]))
