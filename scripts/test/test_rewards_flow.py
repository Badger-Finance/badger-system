from brownie import *
from scripts.systems.badger_system import connect_badger
from config.badger_config import badger_config
from rich.console import Console
from scripts.systems.badger_system import connect_badger
from scripts.test.test_all_claims import test_claim
from assistant.rewards.aws_utils import download_past_trees
from assistant.rewards.rewards_assistant import run_action
from helpers.constants import *

import tabulate
import random
import json

# Results comparison
# Propose root (staging)
# Upload root (staging)
# test all claims

tokens_to_check = [BADGER, DIGG, FARM, XSUSHI, DFD]
console = Console()


def main():
    badger = connect_badger()
    tree = badger.badgerTree

    trees = download_past_trees(2)
    pastRewards = json.loads(trees[1])
    previousRewards = json.loads(trees[0])

    startBlock = int(previousRewards["startBlock"])
    endBlock = int(previousRewards["endBlock"])

    # Generate rewards with new mechanic
    newRewards = run_action(
        badger,
        {
            "action": "rootUpdater",
            "startBlock": startBlock,
            "endBlock": endBlock,
            "pastRewards": pastRewards,
        },
        test=True,
    )

    # compare previousRewards with newRewards

    compare_rewards_trees(previousRewards, newRewards)

    # test claims

    rootProposer = accounts.at(tree.getRoleMember(ROOT_PROPOSER_ROLE, 0), force=True)
    rootValidator = accounts.at(tree.getRoleMember(ROOT_VALIDATOR_ROLE, 0), force=True)

    lastProposeEndBlock = tree.lastProposeEndBlock()
    currentCycle = tree.currentCycle()

    tree.proposeRoot(
        newRewards["merkleRoot"],
        newRewards["rootHash"],
        currentCycle + 1,
        lastProposeEndBlock + 1,
        endBlock,
        {"from": rootProposer},
    )

    tree.approveRoot(
        newRewards["merkleRoot"],
        newRewards["rootHash"],
        currentCycle + 1,
        lastProposeEndBlock + 1,
        endBlock,
        {"from": rootValidator},
    )
    assert tree.merkleRoot() == newRewards["merkleRoot"]
    assert tree.currentCycle() == currentCycle + 1

    retroactive_claims = newRewards["merkleTree"]["claims"]
    users_to_verify = []
    pct_claims_to_verify = 0.001

    for user, claim in retroactive_claims.items():
        roll = random.random()
        if roll < pct_claims_to_verify:
            console.print(roll, pct_claims_to_verify)
            users_to_verify.append(user)
            test_claim(badger, user, claim, tokens_to_check)

    # Claim as same set of users from previous test with updated root
    for user, claim in retroactive_claims.items():
        # test_claim(badger, user, claim, tokens_to_check)
        if user in users_to_verify:
            test_claim(badger, user, claim, tokens_to_check)


def compare_rewards_trees(old, new):
    rewardsInfo = []
    data = {}
    for addr, data in old["claims"].items():
        oldBadgerAmount = data["cumulativeAmounts"][data["tokens"].index(BADGER)]
        oldDiggAmount = data["cumulativeAmounts"][data["tokens"].index(DIGG)]

        data[addr] = {"oldBadger": oldBadgerAmount, "oldDigg": oldDiggAmount}
    for addr, data in new["claims"].items():
        newBadgerAmount = data["cumulativeAmounts"][data["tokens"].index(BADGER)]
        newDiggAmount = data["cumulativeAmounts"][data["tokens"].index(DIGG)]
        data[addr] = {"badger": newBadgerAmount, "digg": newDiggAmount}
