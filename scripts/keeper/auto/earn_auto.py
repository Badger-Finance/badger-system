from helpers.time_utils import to_minutes
from brownie import *
from config.keeper import keeper_config
from helpers.gas_utils import gas_strategies
from helpers.run_persistent import run_persistent
from rich.console import Console
from scripts.keeper.earn import earn_all
from scripts.systems.badger_system import connect_badger
from tabulate import tabulate

console = Console()

gas_strategies.set_default_for_active_chain()


def main():
    badger = connect_badger(load_keeper=True)
    skip = keeper_config.get_active_chain_skipped_setts("earn")
    run_interval = keeper_config.get_active_chain_run_interval("earn")

    console.print("=== Earn (Eternal) ===")
    console.print("All Setts on chain", badger.getAllSettIds())
    console.print("Setts to skip", skip)
    console.print("Interval between runs: {} minutes".format(to_minutes(run_interval)))

    run_persistent(earn_all, (badger, skip), run_interval=run_interval)
