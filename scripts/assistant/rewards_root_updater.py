from assistant.rewards.rewards_assistant import run_action
from scripts.systems.badger_system import connect_badger
import json
import sys

from brownie import *


def main():
    # Load Badger system from config
    # fileName = "deploy-" + str(chain.id) + ".json"
    # original_stdout = sys.stdout # Save a reference to the original standard output

    # with open('filename.txt', 'w') as f:
    #     sys.stdout = f # Change the standard output to the file we created.

    fileName = "deploy-final.json"
    badger = connect_badger(fileName)
    claimAt = chain.height
    run_action(badger, {"action": "rootUpdater", "endBlock": claimAt})
    run_action(badger, {"action": "guardian", "startBlock": claimAt})
