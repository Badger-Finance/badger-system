from scripts.rewards.rewards_utils import get_last_proposed_cycle
import time

from brownie import *
from rich.console import Console
from scripts.systems.badger_system import connect_badger

from assistant.rewards.rewards_assistant import run_action

console = Console()


def main():
    badger = connect_badger()
    (currentRewards, startBlock, endBlock) = get_last_proposed_cycle(badger)

    # If there is a pending root, approve after independently verifying it
    rootApproved = run_action(
        badger,
        {
            "action": "guardian",
            "startBlock": startBlock,
            "endBlock": endBlock,
            "pastRewards": currentRewards,
        },
        test=True,
    )
