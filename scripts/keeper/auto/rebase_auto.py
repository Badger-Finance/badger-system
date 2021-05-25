from helpers.time_utils import to_days, to_minutes
from brownie import Wei, accounts, interface, rpc
from config.badger_config import badger_config
from helpers.constants import *
from helpers.constants import MaxUint256
from helpers.gas_utils import gas_strategies
from helpers.run_persistent import run_persistent
from helpers.utils import val
from rich.console import Console
from scripts.keeper.rebase import rebase
from scripts.systems.badger_system import connect_badger
from scripts.systems.digg_system import connect_digg
from tabulate import tabulate

console = Console()

gas_strategies.set_default_for_active_chain()


def main():
    console.print("[white]===== Checking Parameters for rebase =====[/white]")
    badger = connect_badger(load_deployer=True)

    console.print("=== Rebase (Eternal) ===")
    console.print("Interval between runs: {} minutes".format(to_minutes(120)))

    run_persistent(rebase, (badger, badger.deployer), run_interval=120)
