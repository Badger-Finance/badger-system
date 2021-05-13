from brownie import *
from config.keeper import keeper_config
from helpers.gas_utils import gas_strategies
from helpers.registry import registry
from helpers.sett.SnapshotManager import SnapshotManager
from helpers.utils import tx_wait, val
from helpers.console_utils import console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate

gas_strategies.set_default_for_active_chain()


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
                {"from": keeper, "gas_limit": 2000000, "allow_revert": True},
                confirm=False,
            )
        else:
            snap.settHarvest(
                {"from": keeper, "gas_limit": 2000000, "allow_revert": True},
                confirm=False,
            )

        tx_wait()

        if rpc.is_active():
            chain.mine()
        after = snap.snap()

        snap.printCompare(before, after)


def main():
    badger = connect_badger(load_keeper=True)

    if rpc.is_active():
        """
        Test: Load up testing accounts with ETH
        """
        accounts[0].transfer(badger.deployer, Wei("5 ether"))
        accounts[0].transfer(badger.keeper, Wei("5 ether"))
        accounts[0].transfer(badger.guardian, Wei("5 ether"))

    skip = keeper_config.get_active_chain_skipped_setts("harvest")
    harvest_all(badger, skip)
