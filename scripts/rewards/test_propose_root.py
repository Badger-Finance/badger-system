from scripts.rewards.rewards_utils import fetch_rewards_preconditions
import time

from brownie import *
from config.badger_config import badger_config
from rich.console import Console
from scripts.systems.badger_system import connect_badger

from assistant.rewards.rewards_assistant import fetch_current_rewards_tree, run_action

console = Console()


def main():
    badger = connect_badger(badger_config.prod_json, load_keeper=False)
    (startBlock, endBlock) = fetch_rewards_preconditions(badger)

    # If sufficient time has passed since last root proposal, propose a new root
    rootProposed = run_action(
        badger,
        {"action": "rootUpdater", "startBlock": startBlock, "endBlock": endBlock},
        test=True,
    )
