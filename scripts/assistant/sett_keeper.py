from helpers.time_utils import daysToSeconds
import os
import json
from scripts.systems.badger_system import connect_badger
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


def main():
    test = True
    # if rpc.is_active():
    #     sender = accounts[0]
    # else:
    #     priv = os.environ.get('VAULT_KEEPER_PRIV')
    #     sender = accounts.add(priv) if priv else accounts.load(input('brownie account: '))

    badger = connect_badger("local.json")
    keeper = badger.keeper

    # TODO Load keeper account from file

    if test:
        chain.sleep(daysToSeconds(0.1))

    for key, vault in badger.sett_system.vaults.items():
        strategy = badger.getStrategy(key)
        check_earn(vault, strategy, keeper)

    if test:
        chain.sleep(daysToSeconds(2))

    for key, vault in badger.sett_system.vaults.items():
        strategy = badger.getStrategy(key)
        if test:
            chain.mine()
        check_tend(vault, strategy, keeper)
        if test:
            chain.mine()
        check_harvest(vault, strategy, keeper)

    if test:
        chain.sleep(daysToSeconds(1))

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

