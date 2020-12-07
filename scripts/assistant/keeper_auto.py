from helpers.tx_utils import send
from scripts.assistant.vault_test import (
    claim_assets_from_whales,
    get_balances,
    print_balances,
)
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
from config.ethereum import eth_config
from config.badger_config import badger_config

console = Console()

warnings.simplefilter("ignore")
# keeper = accounts.load("keeper")

def get_expected_gains():
    return badger.getSettRewards("native.badger")

def check_earn(sett, strategy, account):
    """
    Run earn() if sufficent deposits in Sett
    - If we have deposits > a threshold, earn()
    - Check gas costs
    """
    send(sett, sett.earn.encode_input(), "deployer")


def check_harvest(sett, strategy, account):
    """
    - Run harvest() if sufficent value accumulated
    - Estimate value gained with staticcall
    - Check vs gas cost
    """
    send(strategy, strategy.harvest.encode_input(), "keeper")

"""
FARM
Run harvest if the underlying vault has harvested

Normal
Run harvest daily

Badger
Run harvest 2/3x a day

Tend
2/4x a day
"""

def check_tend(sett, strategy, account):
    """
    - Run tend() if sufficient value accumulated
    - Estimate value gained with staticcall
    - Check vs gas cost
    """
    if strategy.isTendable():
        send(strategy, strategy.tend.encode_input(), "keeper")


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


def earn_all(badger: BadgerSystem, test, user, skip):
    keeper = badger.deployer
    for key, vault in badger.sett_system.vaults.items():
        if test:
            assert vault.balanceOf(user) > 0
        if key in skip:
            print("Skip ", key)
            continue
        console.print("\n[bold red]===== Earn: " + key + " =====[/bold red]\n")
        strategy = badger.getStrategy(key)
        controller = Controller.at(vault.controller())
        want = interface.IERC20(vault.token())

        # Pre safety checks
        assert want == strategy.want()
        assert strategy.controller() == controller
        assert vault.controller() == controller
        if want.balanceOf(vault) == 0:
            print("No balance in Sett: ", key)
            continue
        assert controller.strategies(want) == strategy

        destination = get_expected_strategy_deposit_location(badger, key)
        print([destination])

        vaultBefore = want.balanceOf(vault)
        destinationBefore = want.balanceOf(destination)
        strategyBefore = strategy.balanceOf()
        controllerBefore = want.balanceOf(controller)

        print("Check Earn: " + key, vault, strategy)
        toEarn = False
        if vaultBefore / strategyBefore > 0.025:
            print("Earn: " + key, vault, strategy)
            toEarn = True
            check_earn(vault, strategy, keeper)

        # Post safety for test run
        vaultAfter = want.balanceOf(vault)
        destinationAfter = want.balanceOf(destination)
        strategyAfter = strategy.balanceOf()
        controllerAfter = want.balanceOf(controller)

        table = []
        
        table.append(
            ["vault", val(vaultBefore), val(vaultAfter), val(vaultAfter - vaultBefore)]
        )
        table.append(
            [
                "destination",
                val(destinationBefore),
                val(destinationAfter),
                val(destinationAfter - destinationBefore),
            ]
        )
        table.append(
            [
                "strategy",
                val(strategyBefore),
                val(strategyAfter),
                val(strategyAfter - strategyBefore),
            ]
        )
        table.append(
            [
                "controller",
                val(controllerBefore),
                val(controllerAfter),
                val(controllerAfter - controllerBefore),
            ]
        )

        print(tabulate(table, headers=["name", "before", "after", "diff"]))
        if toEarn:
            assert strategyAfter > strategyBefore


def main():
    test = False
    earn = True
    tend = False
    harvest = False

    fileName = "deploy-" + "final" + ".json"
    badger = connect_badger(fileName)
    # keeper = badger.keeper

    user = ""
    skip = []
  
    if earn:
        earn_all(badger, test, user, skip)