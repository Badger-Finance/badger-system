from assistant.rewards.rewards_assistant import run_action
from scripts.systems.badger_system import connect_badger
import json

from brownie import *


def main():
    # Load Badger system from config
    fileName = "deploy-" + str(chain.id) + ".json"
    badger = connect_badger(fileName)
    claimAt = chain.height
    run_action(badger, {"action": "rootUpdater", "endBlock": claimAt})
    run_action(badger, {"action": "guardian", "endBlock": claimAt})
