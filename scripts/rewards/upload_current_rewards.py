from assistant.rewards.aws_utils import upload
from scripts.rewards.rewards_utils import calc_next_cycle_range
import time
import json
from brownie import *
from config.badger_config import badger_config
from rich.console import Console
from scripts.systems.badger_system import connect_badger

from assistant.rewards.rewards_assistant import run_action

console = Console()


def main():
    badger = connect_badger(
        badger_config.prod_json, load_keeper=False, load_deployer=False
    )
    outputName = "rewards-1-0x77218a9a95f4a10df4ec8795cbc4bda027532c9353569c1be9ac691381e2686f.json"

    with open(outputName) as f:
        rewards = json.load(f)

    upload(outputName)
