from helpers.time_utils import to_minutes
from brownie import *
from config.keeper import keeper_config
from helpers.gas_utils import gas_strategies
from helpers.run_persistent import run_persistent
from helpers.utils import tx_wait
from rich.console import Console
from scripts.keeper.harvest import harvest_all
from scripts.systems.badger_system import connect_badger
from tabulate import tabulate

gas_strategies.set_default_for_active_chain()

console = Console()


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
    run_interval = keeper_config.get_active_chain_run_interval("harvest")

    console.print("=== Harvest (Eternal) ===")
    console.print("All Setts on chain", badger.getAllSettIds())
    console.print("Setts to skip", skip)
    console.print("Interval between runs: {} minutes".format(to_minutes(run_interval)))

    run_persistent(harvest_all, [badger, skip], run_interval=run_interval)
