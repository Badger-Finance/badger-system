from scripts.assistant.vault_test import claim_assets_from_whales, get_balances, print_balances
from assistant.rewards.rewards_checker import val
from helpers.time_utils import daysToSeconds, hours
import os
import json
from scripts.systems.badger_system import BadgerSystem, connect_badger
import warnings
from tabulate import tabulate
from brownie import *
from helpers.registry import registry
from rich.console import Console
console = Console()

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


def get_expected_strategy_deposit_location(badger: BadgerSystem, id):
    if id == "native.badger":
        # Rewards Staking
        return badger.getSettRewards("native.badger")
    if id == "native.uniBadgerWbtc":
        # Rewards Staking
        return badger.getSettRewards("native.uniBadgerWbtc")
    if id == "native.renCrv":
        # CRV Gauge
        return registry.curve.pools.renCrv.gauge
    if id == "native.sbtcCrv":
        # CRV Gauge
        return registry.curve.pools.sbtcCrv.gauge
    if id == "native.tbtcCrv":
        # CRV Gauge
        return registry.curve.pools.tbtcCrv.gauge
    if id == "harvest.renCrv":
        # Harvest Vault
        return registry.harvest.vaults.renCrv


def main():
    test = False
    # if rpc.is_active():
    #     sender = accounts[0]
    # else:
    #     priv = os.environ.get('VAULT_KEEPER_PRIV')
    #     sender = accounts.add(priv) if priv else accounts.load(input('brownie account: '))
    fileName = "deploy-" + "final" + ".json"
    badger = connect_badger(fileName)
    # keeper = badger.keeper
    BadgerTree.deploy({'from': badger.deployer})

