from helpers.sett.SnapshotManager import SnapshotManager
from brownie import *
from brownie.network.gas.strategies import GasNowStrategy
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate
from helpers.registry import registry
from assistant.rewards.rewards_checker import val
gas_strategy = GasNowStrategy("fast")

console = Console()
def harvest_all(badger: BadgerSystem, skip):
    for key, vault in badger.sett_system.vaults.items():
        if key in skip:
            continue

        console.print("\n[bold yellow]===== Harvest: " + str(key) + " =====[/bold yellow]\n")

        print("Harvest: " + key)

        snap = SnapshotManager(badger, key)
        strategy = badger.getStrategy(key)
        keeper = accounts.at(strategy.keeper())

        before = snap.snap()
        snap.settHarvest({'from': keeper, "gas_price": gas_strategy})
        after = snap.snap()

        snap.printCompare(before, after)

def main():
    """
    Simulate tend operation and evaluate tendable amount
    """

    # TODO: Output message when failure

    fileName = "deploy-" + "final" + ".json"
    badger = connect_badger(fileName, load_keeper=True)

    skip = [
        # "native.uniBadgerWbtc"
        # "harvest.renCrv",
        # "native.sbtcCrv",
        # "native.sBtcCrv",
        # "native.tbtcCrv",
        # "native.renCrv",
        # "native.badger",
    ]
    harvest_all(badger, skip)