from assistant.rewards.rewards_assistant import run_action
from scripts.systems.badger_system import connect_badger
import json

from brownie import *
from helpers.constants import GUARDIAN_ROLE
from brownie.network import account
from dotmap import DotMap
from assistant.rewards.config import config


def main():
    # Load Badger system from config
    badger = connect_badger("local.json")
    claimAt = chain.height
    run_action(badger, {"action": "rootUpdater", "endBlock": claimAt})
    run_action(badger, {"action": "guardian", "endBlock": claimAt})
