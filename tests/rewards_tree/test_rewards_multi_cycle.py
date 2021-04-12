import json
import secrets

import brownie
from dotmap import DotMap
import pytest

import pprint

from brownie import *
from helpers.constants import *
from helpers.registry import registry
from rich.console import Console

console = Console()

@pytest.fixture(scope="function", autouse="True")
def setup():
    from assistant.rewards import rewards_assistant
    return rewards_assistant

# @pytest.mark.skip()
def test_rewards_flow(setup):
    rewards_assistant = setup
    # badgerTree = rewards_assistant.BadgerTree
    badgerTree = BadgerTreeV2
    guardian = rewards_assistant.guardian
    rootUpdater = rewards_assistant.rootUpdater

    admin, proposer, validator, user = accounts[:4]

    rewardsContract = admin.deploy(BadgerTreeV2)
    rewardsContract.initialize(admin, proposer, validator)

    contentHash1 = "0xe8e31919bd92024a0437852392695f5424932b2d1b041ab45c319de7ce42fda0"
    contentHash2 = "0xe84f535a2581589e2c0b62040926d6599d14c436da24ab8fac5e2c86467721aa"
    

    with open("rewards/test-rewards-{}.json".format(contentHash1)) as f:
        rewards1 = json.load(f)

    with open("rewards/test-rewards-{}.json".format(contentHash2)) as f:
        rewards2 = json.load(f)

    console.print("Here are the merkle roots to use")
    console.print({
        "root1": rewards1["merkleRoot"],
        "root2": rewards2["merkleRoot"]
    })
    
    """
    The new tree enables a couple significant features:
    - Claim from past cycles
    - Partially claim (only some tokens)
    - Partially claim (only some amounts)
        - In the future we may stake certain rewards in farms via the tree

    == Test Setup ==
    Create a tree and fund with Badger, Digg, xSushi, FARM tokens via distribute_from_whales()
    Set to real past root (unlike the live tree, claimed will be zero for everyone)

    == First root to use ==
    0xe68a891a97fceba2afa40bfe627f1c7ee98989a727c03408314b2e6ffa56caab

    == Run the following tests ==
    Run claims for users with various parameters (full claims, only claiming some tokens, only claiming partial amounts, etc)
    Ensure that the expected gains of tokens occur in each case
    Try to claim more than the appropriate amount sometimes, and ensure the failure occurs
    Run claims for past cycle and ensure they work as expected

    == Update to new root == 
    0xefe2c10736c6176d415009dbe85037f0b9150631cf334176783c5ae1cb3cb895

    Go through proposeRoot and approveRoot to get new data uploaded.
    
    Try the same series of tests from before and make sure the amonuts recieved and amounts claimable are correct given the new cycle, especially for users who claimed during previous cycle
    Also make sure that users can claim from the previous cycle still with that data
    """

    assert False
