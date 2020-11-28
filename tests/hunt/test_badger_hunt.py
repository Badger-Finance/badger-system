import json
import secrets

import brownie
import pytest
from assistant.rewards import rewards_assistant
from brownie import *
from config import badger_config
from helpers.constants import *
from helpers.time_utils import daysToSeconds
from rich.console import Console
from tests.rewards_tree.fixtures import rewards_tree_unit

console = Console()

with open("merkle/airdrop.json") as f:
    Airdrop = json.load(f)


@pytest.fixture(scope="function", autouse="True")
def setup(badger_hunt_unit):
    return badger_hunt_unit


def test_initial_parameters(setup):
    """
    Ensure all values are written correctly
    """
    hunt = setup.badgerHunt

    assert hunt.owner() == setup.devMultisig
    assert hunt.token() == setup.token
    assert hunt.rewardsEscrow() == setup.rewardsEscrow
    assert hunt.epochDuration() == daysToSeconds(1)
    assert hunt.gracePeriod() == daysToSeconds(2)
    assert hunt.rewardReductionPerEpoch() == 2000
    assert hunt.currentRewardRate() == 10000
    assert hunt.finalEpoch() == 4


def test_claims_e2e(setup):
    """
    Ensure claims flow
    - Each user can claim once
    - User without a claim shouldn't be able to claim
    - User with wrong proof shouldn't be able to claim
    - User should not be able to claim twice
    - User should be tracked correctly as claimed or not claimed
    - Epochs should update at appropriate times
    - Epochs, times, and reward percentages should update correctly with the passage of time
    - Excess rewards should go to RewardsEscrow
    """
    hunt = setup.badgerHunt
    badger = setup.token
    deployer = setup.deployer

    users = [
        "0x97137466Bc8018531795217f0EcC4Ba24Dcba5c1",
        "0x36cc7B13029B5DEe4034745FB4F24034f3F2ffc6",
        "0xC845594A546Af8cAAC5e2C85971CfCe4CFb250A6",
    ]

    MAX_BPS = hunt.MAX_BPS()

    for user in users:
        accounts.at(user, force=True)

        claim = Airdrop["claims"][user]
        index = claim["index"]
        amount = int(claim["amount"], 16)
        proof = claim["proof"]

        console.log(locals())

        # Should not be able to claim with invalid address
        with brownie.reverts():
            hunt.claim(index, deployer.address, amount, proof, {"from": user})

        # Should not be able to claim with invalid index
        with brownie.reverts():
            hunt.claim(index + 1, user, amount, proof, {"from": user})

        # Should not be able to claim with invalid amount
        with brownie.reverts():
            hunt.claim(index, user, amount + 1, proof, {"from": user})

        # Should not be able to claim from another account
        with brownie.reverts():
            hunt.claim(index, user, amount, proof, {"from": deployer})

        preBalance = badger.balanceOf(user)

        hunt.claim(index, user, amount, proof, {"from": user})

        postBalance = badger.balanceOf(user)
        rewardsRate = hunt.currentRewardRate()
        expectedRewards = int(amount * rewardsRate // MAX_BPS)

        assert preBalance + expectedRewards == postBalance


@pytest.mark.skip()
def test_all_claims(setup):
    """
    Ensure all claims
    - Each user should be able to claim their amount
    - Total claimed @ day 1 should equal total hunt supplys
    """

    # For each user
    # Unlock their account
    # Load their account (force=True)
    # Make their claim
    # Ensure their claim is correct
    # Track total claimed

    for user, userData in Airdrop["claims"].items():
        index = userData['index']


