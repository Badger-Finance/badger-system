from helpers.time_utils import to_minutes
from helpers.run_persistent import run_persistent
from config.keeper import keeper_config
from helpers.utils import val
from brownie import *
from helpers.gas_utils import gas_strategies
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from tabulate import tabulate
from scripts.keeper.tend import tend_all

gas_strategies.set_default_for_active_chain()

console = Console()


def main():
    badger = connect_badger(load_keeper=True)
    skip = keeper_config.get_active_chain_skipped_setts("tend")
    run_interval = keeper_config.get_active_chain_run_interval("tend")

    console.print("=== Tend (Eternal) ===")
    console.print("All Setts on chain", badger.getAllSettIds())
    console.print("Setts to skip", skip)
    console.print("Interval between runs: {} minutes".format(to_minutes(run_interval)))

    run_persistent(tend_all, (badger, skip), num_args=2, run_interval=run_interval)
