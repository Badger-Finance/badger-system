from helpers.sett.SnapshotManager import SnapshotManager
from brownie import *
from brownie.network.gas.strategies import GasNowStrategy
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate
from helpers.registry import registry
from assistant.rewards.rewards_checker import val

console = Console()

earn_deposit_threshold = 0.05

gas_strategy = GasNowStrategy("fast")

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
    if id == "native.sushiWbtcEth":
        # Sushi Chef
        return registry.sushi.sushiChef
    if id == "native.sushiBadgerWbtc":
        # Sushi Chef
        return registry.sushi.sushiChef

def earn_preconditions(vaultBalance, strategyBalance):
    # Always allow earn on first run
    if strategyBalance == 0:
        return True
    # Earn if deposits have accumulated over % threshold
    if vaultBalance / strategyBalance > earn_deposit_threshold:
        return True
    else:
        return False

def earn_all(badger: BadgerSystem, skip):
    keeper = badger.deployer
    for key, vault in badger.sett_system.vaults.items():
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
        assert controller.strategies(want) == strategy

        vaultBefore = want.balanceOf(vault)
        strategyBefore = strategy.balanceOf()

        toEarn = False
        if earn_preconditions(vaultBefore, strategyBefore):
            print("Earn: " + key, vault, strategy)
            toEarn = True

            snap = SnapshotManager(badger, key)
            strategy = badger.getStrategy(key)
            keeper = accounts.at(strategy.keeper())

            before = snap.snap()
            snap.printTable(before)

            keeper = accounts.at(vault.keeper())
            snap.settEarn({'from': keeper, "gas_price": gas_strategy, "gas_limit": 2000000, "allow_revert": True}, confirm=False)

            after = snap.snap()
            snap.printTable(after)

            snap.printCompare(before, after)

            


def main():
    # TODO: Output message when failure

    fileName = "deploy-" + "final" + ".json"
    badger = connect_badger(fileName, load_keeper=True)

    skip = [
        # "native.uniBadgerWbtc",
        # "harvest.renCrv",
        # "native.sbtcCrv",
        # "native.sBtcCrv",
        # "native.tbtcCrv",
        # "native.renCrv",
        # "native.badger",
        "native.sushiBadgerWbtc",
        # "native.sushiWbtcEth",
        # "native.digg",
        # "native.uniDiggWbtc", 
        # "native.sushiDiggWbtc"
    ]
    earn_all(badger, skip)