from helpers.utils import tx_wait
from helpers.sett.SnapshotManager import SnapshotManager
from brownie import *
from brownie.network.gas.strategies import GasNowStrategy
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, LoadMethod, connect_badger
from tabulate import tabulate
from helpers.registry import registry
from assistant.rewards.rewards_checker import val

gas_strategy = GasNowStrategy("fast")

console = Console()


def harvest_all(badger: BadgerSystem, skip):
    for key, vault in badger.sett_system.vaults.items():
        if key in skip:
            continue

        console.print(
            "\n[bold yellow]===== Harvest: " + str(key) + " =====[/bold yellow]\n"
        )

        print("Harvest: " + key)

        snap = SnapshotManager(badger, key)
        strategy = badger.getStrategy(key)
        keeper = accounts.at(badger.keeper)

        before = snap.snap()
        if strategy.keeper() == badger.badgerRewardsManager:
            snap.settHarvestViaManager(
                strategy,
                {
                    "from": keeper,
                    "gas_price": gas_strategy,
                },
                confirm=False,
            )
        else:
            snap.settHarvest(
                {
                    "from": keeper,
                    "gas_price": gas_strategy,
                },
                confirm=False,
            )

        tx_wait()

        if rpc.is_active():
            chain.mine()
        after = snap.snap()

        snap.printCompare(before, after)


def main():
    """
    Simulate tend operation and evaluate tendable amount
    """

    # TODO: Output message when failure

    # TODO: Use test mode if RPC active, no otherwise

    fileName = "deploy-" + "final" + ".json"
    badger = connect_badger(fileName, load_keeper=True, load_method=LoadMethod.SK)

    if rpc.is_active():
        """
        Test: Load up sending accounts with ETH and whale tokens
        """
        accounts[0].transfer(badger.deployer, Wei("5 ether"))
        accounts[0].transfer(badger.keeper, Wei("5 ether"))
        accounts[0].transfer(badger.guardian, Wei("5 ether"))

    skip = [
        "native.uniBadgerWbtc",
        # "harvest.renCrv",
        # "native.sbtcCrv",
        # "native.sBtcCrv",
        # "native.tbtcCrv",
        # "native.renCrv",
        "native.badger",
        "native.sushiBadgerWbtc",
        # "native.sushiWbtcEth",
        "native.digg",
        "native.uniDiggWbtc",
        "native.sushiDiggWbtc",
    ]
    harvest_all(badger, skip)
