from helpers.sett.SnapshotManager import SnapshotManager
from config.keeper import keeper_config
from helpers.utils import tx_wait, val
from brownie import *
from helpers.gas_utils import gas_strategies
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate

gas_strategies.set_default_for_active_chain()

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

        snap = SnapshotManager(badger, key)
        strategy = badger.getStrategy(key)
        keeper = accounts.at(badger.keeper)

        before = snap.snap()

        if strategy.keeper() == badger.badgerRewardsManager:
            snap.settTendViaManager(
                strategy,
                {"from": keeper, "gas_limit": 1000000},
                confirm=False,
            )
        else:
            snap.settTend(
                {"from": keeper, "gas_limit": 1000000},
                confirm=False,
            )

        tx_wait()

        if rpc.is_active():
            chain.mine()
        after = snap.snap()

        snap.printCompare(before, after)


def main():
    badger = connect_badger(load_keeper=True)
    skip = keeper_config.get_active_chain_skipped_setts("tend")
    console.print(badger.getAllSettIds())

    tend_all(badger, skip)
