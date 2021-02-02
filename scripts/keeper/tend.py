from brownie import *
from brownie.network.gas.strategies import GasNowStrategy
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate

from assistant.rewards.rewards_checker import val

gas_strategy = GasNowStrategy("fast")

console = Console()


def tend_all(badger: BadgerSystem, skip):
    table = []
    for key, vault in badger.sett_system.vaults.items():
        if key in skip:
            continue

        strategy = badger.getStrategy(key)

        if not strategy.isTendable():
            continue

        console.print("\n[bold green]===== Tend: " + key + " =====[/bold green]\n")
        fpps_before = vault.getPricePerFullShare()

        keeper = accounts.at(strategy.keeper())
        strategy.tend({"from": keeper, "gas_price": gas_strategy})

        table.append(
            [
                key,
                val(fpps_before),
                val(vault.getPricePerFullShare()),
                val(vault.getPricePerFullShare() - fpps_before),
            ]
        )

        print("PPFS: Tend")
        print(tabulate(table, headers=["name", "before", "after", "diff"]))


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
    tend_all(badger, skip)
