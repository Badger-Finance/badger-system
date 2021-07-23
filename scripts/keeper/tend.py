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


def tend_all(badger: BadgerSystem, skip, min_profit=0):
    """
    Runs tend function for strategies if they are expected to be profitable.
    If a profit estimate fails for any reason the default behavior is to treat it as having a profit of zero.

    :param badger: badger system
    :param skip: strategies to skip checking
    :param min_profit: minimum estimated profit (in ETH or BNB) required for harvest to be executed on chain
    """
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

        before = snap.snap()

        if strategy.keeper() == badger.badgerRewardsManager:
            estimated_profit = snap.estimateProfitTendViaManager(
                key, strategy, {"from": keeper, "gas_limit": 1000000}, min_profit
            )
            if estimated_profit >= min_profit:
                snap.settTendViaManager(
                    strategy,
                    {"from": keeper, "gas_limit": 1000000},
                    confirm=False,
                )
        else:
            keeper = accounts.at(strategy.keeper())
            estimated_profit = snap.estimateProfitTend(
                key, {"from": keeper, "gas_limit": 1000000}, min_profit
            )
            if estimated_profit >= min_profit:
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
    badger = connect_badger(load_keeper=True, load_harvester=True)
    skip = keeper_config.get_active_chain_skipped_setts("tend")
    console.print(badger.getAllSettIds())

    if rpc.is_active():
        """
        Test: Load up testing accounts with ETH
        """
        accounts[0].transfer(badger.keeper, Wei("5 ether"))

        skip.append("yearn.wbtc")
        skip.append("native.test")
        skip.append("experimental.sushiIBbtcWbtc")
        skip.append("experimental.digg")

    tend_all(badger, skip)
