from assistant.rewards.rewards_checker import val
from brownie import *
from brownie.network.gas.strategies import GasNowStrategy
from helpers.gas_utils import gas_strategies
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate

gas_strategies.set_default(gas_strategies.exponentialScaling)

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
        strategy.tend({"from": keeper})

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
        "native.uniBadgerWbtc",
        "harvest.renCrv",
        "native.sbtcCrv",
        "native.sBtcCrv",
        "native.tbtcCrv",
        "native.renCrv",
        "native.badger",
        "native.sushiBadgerWbtc",
        "native.sushiWbtcEth",
        "native.digg",
        "native.uniDiggWbtc",
        "native.sushiDiggWbtc",
    ]
    tend_all(badger, skip)
