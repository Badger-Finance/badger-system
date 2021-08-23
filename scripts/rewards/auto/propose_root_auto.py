from scripts.rewards.rewards_utils import calc_next_cycle_range
import time

from brownie import *
from config.badger_config import badger_config
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from scripts.rewards.propose_root import propose_root
from assistant.rewards.rewards_assistant import fetch_current_rewards_tree, run_action
from helpers.discord import send_message_to_discord

console = Console()


def main():
    badger = connect_badger(load_root_proposer=True)

    while True:
        propose_root(badger)
        time.sleep(10 * 60)
        try:
            propose_root(badger)
        except Exception as e:
            console.print("[red]Error[/red]", e)
            send_message_to_discord(
                "**ERROR APPROVING ROOT**",
                "approve_root_auto.py has encountered an error",
                [{"name": "Error", "value": e, "inline": True}],
            )
        finally:
            time.sleep(10 * 60)
