from scripts.rewards.rewards_utils import calc_next_cycle_range
import time

from brownie import *
from rich.console import Console
from scripts.systems.badger_system import connect_badger

from assistant.rewards.rewards_assistant import run_action

console = Console()


def main():
    badger = connect_badger()
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
        test=True,
    )
