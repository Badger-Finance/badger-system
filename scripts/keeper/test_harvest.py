from brownie import *
from config.keeper import keeper_config
# from helpers.gas_utils import gas_strategies
from helpers.registry import registry
from helpers.sett.SnapshotManager import SnapshotManager
from helpers.utils import tx_wait, val
from helpers.console_utils import console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate

# gas_strategies.set_default_for_active_chain()


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

        before = snap.snap()
        if strategy.keeper() == badger.badgerRewardsManager:
            tx = snap.settTendViaManager(
                strategy,
                {"from": keeper, "gas_limit": 6000000, "allow_revert": True},
                confirm=False,
            )
            tx = snap.settHarvestViaManager(
                strategy,
                {"from": keeper, "gas_limit": 6000000, "allow_revert": True},
                confirm=False,
            )
        else:
            keeper = accounts.at(strategy.keeper())
            tx = snap.settTend(
                {"from": keeper, "gas_limit": 6000000, "allow_revert": True},
                confirm=False,
            )
            tx = snap.settHarvest(
                {"from": keeper, "gas_limit": 6000000, "allow_revert": True},
                confirm=False,
            )

        tx_wait()

        if rpc.is_active():
            chain.mine()
        after = snap.snap()

        snap.printCompare(before, after)


def main():
    badger = connect_badger(load_keeper=True, load_harvester=True)

    if rpc.is_active():
        """
        Test: Load up testing accounts with ETH
        """
        accounts[0].transfer(badger.deployer, Wei("5 ether"))
        accounts[0].transfer(badger.keeper, Wei("5 ether"))
        accounts[0].transfer(badger.guardian, Wei("5 ether"))

    skip = keeper_config.get_active_chain_skipped_setts("harvest")

    set_fees = [
        "native.renCrv",
        "native.sbtcCrv",
        "native.tbtcCrv",
        "native.hbtcCrv",
        "native.pbtcCrv",
        "native.obtcCrv",
        "native.bbtcCrv",
        "native.tricrypto",
    ]

    for key in set_fees:
        strategy = badger.getStrategy(key)
        gov = accounts.at(strategy.governance(), force=True)

        strategy.setWithdrawalFee(50, {'from': gov})
        strategy.setAutoCompoundingPerformanceFeeGovernance(0, {'from': gov})


    harvest_all(badger, skip)
