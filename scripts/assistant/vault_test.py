from helpers.time_utils import daysToSeconds
import os
import json
from scripts.systems.badger_system import BadgerSystem, connect_badger
import warnings
from tabulate import tabulate
from brownie import *

warnings.simplefilter("ignore")
# keeper = accounts.load("keeper")


def check_earn(sett, strategy, account):
    """
    Run earn() if sufficent deposits in Sett
    - If we have deposits > a threshold, earn()
    - Check gas costs
    """
    sett.earn({"from": account})


def check_harvest(sett, strategy, account):
    """
    - Run harvest() if sufficent value accumulated
    - Estimate value gained with staticcall
    - Check vs gas cost
    """
    strategy.harvest({"from": account})


def check_tend(sett, strategy, account):
    """
    - Run tend() if sufficient value accumulated
    - Estimate value gained with staticcall
    - Check vs gas cost
    """
    if strategy.isTendable():
        strategy.tend({"from": account})


def claim_assets_from_whales(badger: BadgerSystem, user):
    # We can almost certainly aquire Sett tokens from the staking contracts
    for key, geyser in badger.geysers.items():
        accounts.at(geyser, force=True)
        sett = badger.getSett(key)
        sett.transfer(user, sett.balanceOf(geyser), {"from": geyser})
        print(user)
        print("Whale funds ", sett.balanceOf(user))
        assert sett.balanceOf(user) > 1


def print_balances(balances):
    table = []
    for key, bal in balances.items():
        table.append([key, bal])

    print(tabulate(table, headers=["name", "balance"]))


def get_balances(accounts, token):
    balances = {}
    for key, account in accounts.items():
        balances[key] = token.balanceOf(account)
    return balances


def main():
    fileName = "deploy-" + "final" + ".json"
    badger = connect_badger(fileName)
    keeper = badger.keeper

    user = accounts[5]

    # Give tester Sett tokens
    claim_assets_from_whales(badger, user)

    # Earn all vaults
    for key, vault in badger.sett_system.vaults.items():
        print("Earn: " + key)
        strategy = badger.getStrategy(key)
        check_earn(vault, strategy, keeper)

    chain.sleep(hours(2))
    chain.mine()

    # Tend and harvest all vaults
    for key, vault in badger.sett_system.vaults.items():
        strategy = badger.getStrategy(key)

        print("Tend: " + key)
        check_tend(vault, strategy, keeper)
        chain.mine()

        print("Harvest: " + key)
        if key == "native.badger":
            check_harvest(vault, strategy, keeper)

    chain.sleep(daysToSeconds(0.5))

    # WIthdraw from all vaults
    for key, vault in badger.sett_system.vaults.items():
        controller = Controller.at(vault.controller())
        strategy = badger.getStrategy(key)

        pre = get_balances({"rewards": controller.rewards(), "user": user}, vault)
        print({"before strategy": strategy.balanceOf()})
        print_balances(pre)
        vault.withdraw(vault.balanceOf(user) // 2, {"from": user})
        print({"after strategy": strategy.balanceOf()})
        post = get_balances({"rewards": controller.rewards(), "user": user}, vault)
        print_balances(post)

    chain.sleep(hours(2))
    chain.mine()

    # Tend and harvest all vaults
    for key, vault in badger.sett_system.vaults.items():
        strategy = badger.getStrategy(key)

        print("Tend: " + key)
        check_tend(vault, strategy, keeper)
        chain.mine()

        print("Harvest: " + key)
        if key == "native.badger":
            check_harvest(vault, strategy, keeper)

    chain.sleep(daysToSeconds(0.5))

    # table = []
    # vaults = []
    # for data in badger_deploy:
    #     if data["name"] in skipped:
    #         print("aLINK not supported yet")
    #         continue
    #     token = interface.ERC20(data["erc20address"])
    #     vault = interface.YearnVault(data["vaultContractAddress"])
    #     decimals = token.decimals()
    #     available = vault.available()
    #     balance = vault.balance()
    #     ratio = 1 - vault.min() / vault.max()
    #     can_earn = available / balance > ratio if balance > 0 else False
    #     if can_earn:
    #         vaults.append(data["vaultContractAddress"])
    #     table.append(
    #         [
    #             data["name"],
    #             available / 10 ** decimals,
    #             balance / 10 ** decimals,
    #             can_earn,
    #         ]
    #     )

    # print(tabulate(table, headers=["name", "available", "balance", "can_earn"]))

    # if vaults:
    #     print("poking these vaults:", vaults)
    #     keeper.earn(vaults, {"from": sender, "gas_limit": 2_500_000})
    # else:
    #     print("no vaults to poke, exiting")

