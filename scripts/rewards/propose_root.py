from scripts.rewards.rewards_utils import calc_next_cycle_range
import time

from brownie import *
from config.badger_config import badger_config
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger

from assistant.rewards.rewards_assistant import fetch_current_rewards_tree, run_action

console = Console()


def propose_root(badger: BadgerSystem):
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


def main():
    badger = connect_badger(badger_config.prod_json, load_keeper=True)

    while True:
        try:
            propose_root(badger)
        except Exception as e:
            console.print("[red]Error[/red]", e)
        finally:
            time.sleep(10 * 60)
