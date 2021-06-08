from scripts.rewards.rewards_utils import get_last_proposed_cycle

from brownie import *
from config.badger_config import badger_config
from rich.console import Console
from scripts.systems.badger_system import connect_badger

from assistant.rewards.rewards_assistant import fetch_current_rewards_tree, run_action

console = Console()


def main():
    badger = connect_badger(badger_config.prod_json, load_root_approver=True)
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
        test=False,
    )
