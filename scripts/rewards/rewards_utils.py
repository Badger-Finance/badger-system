import time

from brownie import *
from config.badger_config import badger_config
from rich.console import Console
from scripts.systems.badger_system import connect_badger
from config.rewards_config import rewards_config
from assistant.rewards.rewards_assistant import fetch_current_rewards_tree, run_action

console = Console()

def get_last_proposed_cycle_range(badger):
    # Fetch the appropriate file
    currentRewards = fetch_current_rewards_tree(badger)

    lastClaimEnd = int(currentRewards["endBlock"])
    lastClaimStart = int(currentRewards["startBlock"])

    # Sanity check: Ensure previous cycle was not too long
    assert lastClaimStart > lastClaimEnd - rewards_config.maxStartBlockAge
    
    # Sanity check: Ensure previous end block is not too far in the past
    assert lastClaimEnd > chain.height - rewards_config.maxStartBlockAge


    # Sanity check: Ensure start block is not too close to end block

    print("Claim Section", lastClaimStart, 
    lastClaimEnd)

    return (lastClaimStart, lastClaimEnd)

def calc_next_cycle_range(badger):
    print("Run at", int(time.time()))
    
    # Fetch the appropriate file
    currentRewards = fetch_current_rewards_tree(badger)

    lastClaimEnd = int(currentRewards["endBlock"])
    startBlock = lastClaimEnd + 1

    # Claim at current block
    endBlock = chain.height

    #Sanity check: Ensure start block is not too far in the past
    assert startBlock > endBlock - rewards_config.maxStartBlockAge

    # Sanity check: Ensure start block is not too close to end block

    print("Claim Section", startBlock, endBlock)

    return (startBlock, endBlock)