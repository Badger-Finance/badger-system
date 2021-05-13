from scripts.rewards.rewards_utils import calc_next_cycle_range
import time

from brownie import *
from config.badger_config import badger_config
from rich.console import Console
from scripts.systems.badger_system import connect_badger

from assistant.rewards.rewards_assistant import fetch_current_rewards_tree, run_action

console = Console()


def main():
    badger = connect_badger(
        badger_config.prod_json, load_keeper=True, load_guardian=True
    )
    (currentRewards, startBlock, endBlock) = calc_next_cycle_range(badger)

    # If sufficient time has passed since last root proposal, propose a new root
    rootProposed = run_action(
        badger,
        {
            "action": "rootUpdater",
            "startBlock": startBlock,
            "endBlock": endBlock,
            "pastRewards": currentRewards,
        },
        test=False,
    )

    time.sleep(45)

    rootApproved = run_action(
        badger,
        {
            "action": "guardian",
            "startBlock": startBlock,
            "endBlock": endBlock,
            "pastRewards": currentRewards,
        },
        test=False,
    )
