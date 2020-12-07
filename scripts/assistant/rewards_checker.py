from helpers.gnosis_safe import convert_to_test_mode, exec_direct
from assistant.rewards.rewards_checker import compare_rewards, push_rewards, test_claims
from helpers.time_utils import daysToSeconds
import os
import json
from scripts.systems.badger_system import connect_badger
import warnings
from tabulate import tabulate
from brownie import *
from helpers.registry import registry


def main():
    fileName = "deploy-" + "final" + ".json"
    badger = connect_badger(fileName)
    multisig = badger.devMultisig
    beforeContentHash = "0xde9ca62139c8daf2a480107c38ee184c3b47658f0739ac18602497993114e690"
    afterContentHash = "0x572d0f08e7107d34090dea90836156be1a7ae90543d55c96db32269e16c6e86c"

    with open("rewards-1-" + beforeContentHash + ".json") as f:
        before_file = json.load(f)
    with open("rewards-1-" + afterContentHash + ".json") as f:
        after_file = json.load(f)

    compare_rewards(badger, int(after_file["startBlock"]), int(after_file["endBlock"]), before_file, after_file, beforeContentHash)
    push_rewards(badger, afterContentHash)
    test_claims(badger, int(after_file["startBlock"]), int(after_file["endBlock"]), before_file, after_file)
