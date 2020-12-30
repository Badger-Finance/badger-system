import time

from brownie import *
from config.badger_config import badger_config
from rich.console import Console
from scripts.systems.badger_system import connect_badger
from config.rewards_config import rewards_config
from assistant.rewards.rewards_assistant import fetch_current_rewards_tree, run_action

console = Console()

def fetch_rewards_preconditions(badger):
    print("Run at", int(time.time()))
    
    # Fetch the appropriate file
    currentRewards = fetch_current_rewards_tree(badger)

    lastClaimEnd = int(currentRewards["endBlock"])
    startBlock = lastClaimEnd + 1

    # Claim at current block
    endBlock = chain.height

    # Sanity check: Ensure start block is not too far in the past
    assert startBlock > endBlock - rewards_config.maxStartBlockAge

    # Sanity check: Ensure start block is not too close to end block

    print("Claim Section", startBlock, endBlock)

    return (startBlock, endBlock)