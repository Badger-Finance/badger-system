import time
from scripts.rewards.rewards_utils import get_last_proposed_cycle

from brownie import *
from config.badger_config import badger_config
from rich.console import Console
from scripts.systems.badger_system import connect_badger
from helpers.gas_utils import gas_strategies

from assistant.rewards.rewards_assistant import fetch_current_rewards_tree, run_action

console = Console()

gas_strategies.set_default(gas_strategies.exponentialScaling)

def approve_root(badger):
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


def main():
    badger = connect_badger(badger_config.prod_json, load_guardian=True)
    
    approve_root(badger)
    time.sleep(10 * 60)

    while True:
        try:
            approve_root(badger)
        except Exception as e:
            console.print("[red]Error[/red]", e)
        finally:
            time.sleep(10 * 60)
