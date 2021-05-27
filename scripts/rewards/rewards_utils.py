import time

from brownie import *
from config.badger_config import badger_config
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem, connect_badger
from config.rewards_config import rewards_config
from assistant.rewards.rewards_assistant import (
    fetch_current_rewards_tree,
    fetch_pending_rewards_tree,
    run_action,
)

console = Console()


def get_last_published_cycle(badger):
    # Fetch the appropriate file
    currentRewards = fetch_current_rewards_tree(badger)

    lastClaimEnd = int(currentRewards["endBlock"])
    lastClaimStart = int(currentRewards["startBlock"])

    # Sanity check: Ensure previous cycle was not too long
    assert lastClaimStart > lastClaimEnd - rewards_config.maxStartBlockAge

    # Sanity check: Ensure previous end block is not too far in the past
    assert lastClaimEnd > chain.height - rewards_config.maxStartBlockAge

    # Sanity check: Ensure start block is not too close to end block
    return (currentRewards, lastClaimStart, lastClaimEnd)


def get_last_proposed_cycle(badger: BadgerSystem):
    # Fetch the appropriate file
    currentRewards = fetch_pending_rewards_tree(badger)

    lastClaimEnd = badger.badgerTree.lastProposeEndBlock()
    lastClaimStart = badger.badgerTree.lastProposeStartBlock()

    # Sanity check: Ensure previous cycle was not too long
    assert lastClaimStart > lastClaimEnd - rewards_config.maxStartBlockAge

    # Sanity check: Ensure previous end block is not too far in the past
    assert lastClaimEnd > chain.height - rewards_config.maxStartBlockAge

    # Sanity check: Ensure start block is not too close to end block
    return (currentRewards, lastClaimStart, lastClaimEnd)


def calc_next_cycle_range(badger):
    print("Run at", int(time.time()))

    # Fetch the appropriate file
    currentRewards = fetch_current_rewards_tree(badger)

    lastClaimEnd = badger.badgerTree.lastPublishEndBlock()
    startBlock = lastClaimEnd + 1

    # Claim at current block, minus a buffer for thegraph
    endBlock = chain.height - 100

    # Sanity check: Ensure start block is not too far in the past
    # assert startBlock > endBlock - rewards_config.maxStartBlockAge

    # Sanity check: Ensure start block is not too close to end block
    return (currentRewards, startBlock, endBlock)
