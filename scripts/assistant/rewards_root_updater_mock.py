from assistant.rewards.rewards_assistant import rootUpdaterMock, run_action
from scripts.systems.badger_system import connect_badger
import json

from brownie import *


def main():
    # Load Badger system from config
    fileName = "deploy-" + str(chain.id) + ".json"
    badger = connect_badger(fileName)
    claimAt = chain.height
    rootUpdaterMock(badger, claimAt)
