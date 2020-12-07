import time
from assistant.rewards.rewards_assistant import fetch_current_rewards_tree, run_action
from scripts.systems.badger_system import connect_badger
import json
import sys
from rich.console import Console
from brownie import *

console = Console()

def main():
    deployFileName = "deploy-final.json"
    badger = connect_badger(deployFileName)
    

    # Get latest block rewards were updated
    currentMerkleData = badger.badgerTree.getCurrentMerkleData()
    console.log("currentMerkleData", currentMerkleData)

    print('Run at', int(time.time()))

    currentRewards = fetch_current_rewards_tree(badger)

    lastClaimEnd = int(currentRewards['endBlock'])
    startBlock = lastClaimEnd + 1

    # Claim at current block
    claimAt = chain.height

    print('Claim Section', startBlock, claimAt)

    # If sufficient time has passed since last root proposal, propose a new root
    rootProposed = run_action(badger, {"action": "rootUpdater", "startBlock": startBlock, "endBlock": claimAt})

    # If there is a pending root, approve after independently verifying it
    rootApproved = run_action(badger, {"action": "guardian", "startBlock": startBlock, "endBlock": claimAt})
