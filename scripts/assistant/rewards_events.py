from assistant.rewards.rewards_assistant import run_action
from scripts.systems.badger_system import connect_badger
import json
import sys

from brownie import *


def main():
    fileName = "deploy-final.json"
    badger = connect_badger(fileName)
    claimAt = chain.height
    run_action(badger, {"action": "rootUpdater", "endBlock": claimAt})
    run_action(badger, {"action": "guardian", "endBlock": claimAt})
