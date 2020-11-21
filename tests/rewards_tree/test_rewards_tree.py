import pytest
from brownie import *
import brownie
from tests.rewards_tree.fixtures import rewards_tree_unit
import secrets
from assistant.rewards import rewards_assistant
from helpers.constants import *


def random_32_bytes():
    return "0x" + secrets.token_hex(32)


@pytest.fixture(scope="function", autouse="True")
def setup(rewards_tree_unit):
    return rewards_tree_unit


def test_root_publish(setup):
    badgerTree = setup.badgerTree
    guardian = setup.guardian
    rootUpdater = setup.rootUpdater
    user = accounts[4]

    startingCycle = badgerTree.currentCycle()
    assert startingCycle == 0

    root = random_32_bytes()
    contentHash = random_32_bytes()

    # Ensure non-root updater cannot update root
    with brownie.reverts():
        badgerTree.publishRoot(root, contentHash, {"from": guardian})

    # Ensure root updater can propose new root, but not update
    badgerTree.publishRoot(root, contentHash, {"from": rootUpdater})

    assert badgerTree.getCurrentMerkleData()[0] == EmptyBytes32
    assert badgerTree.getCurrentMerkleData()[1] == EmptyBytes32
    assert badgerTree.currentCycle() == startingCycle

    assert badgerTree.pendingMerkleRoot() == root
    assert badgerTree.pendingMerkleContentHash() == contentHash


    # Ensure non-root approver cannot approve root
    with brownie.reverts():
        badgerTree.approveRoot(root, contentHash, {"from": guardian})

    badgerTree.approveRoot(root, contentHash, {"from": guardian})

    assert badgerTree.getCurrentMerkleData()[0] == root
    assert badgerTree.getCurrentMerkleData()[1] == contentHash
    assert badgerTree.currentCycle() == startingCycle + 1

    oldRoot = root
    oldContentHash = contentHash

    root = random_32_bytes()
    contentHash = random_32_bytes()

    # Ensure root updater can update another root
    badgerTree.publishRoot(root, contentHash, {"from": rootUpdater})

    assert badgerTree.getCurrentMerkleData()[0] == root
    assert badgerTree.getCurrentMerkleData()[1] == contentHash

    assert badgerTree.currentCycle() == startingCycle + 2

    assert badgerTree.getMerkleData(1)[0] == root
    assert badgerTree.getMerkleData(1)[1] == contentHash

    assert badgerTree.getMerkleData(0)[0] == oldRoot
    assert badgerTree.getMerkleData(0)[1] == oldContentHash


def test_guardian_pause(setup):
    badgerTree = setup.badgerTree
    guardian = setup.guardian
    rootUpdater = setup.rootUpdater
    user = accounts[4]

    # Ensure non-guardian cannot pause
    with brownie.reverts():
        badgerTree.pause({"from": user})

    # Ensure guardian can pause
    badgerTree.pause({"from": guardian})

    # Ensure root updater cannot update root while paused
    with brownie.reverts():
        badgerTree.publishRoot(
            random_32_bytes(), random_32_bytes(), 1, {"from": rootUpdater}
        )

    # Ensure non-root updater cannot update root while paused
    with brownie.reverts():
        badgerTree.publishRoot(random_32_bytes(), random_32_bytes(), 1, {"from": user})

    # Ensure non-guardian cannot unpause
    with brownie.reverts():
        badgerTree.unpause({"from": user})

    # Ensure guardian can unpause
    badgerTree.pause({"from": guardian})

    # Ensure non-root updater cannot update root after unpause
    root = random_32_bytes()
    contentHash = random_32_bytes()
    with brownie.reverts():
        badgerTree.publishRoot(root, contentHash, {"from": user})

    # Ensure root updater can update root after unpause
    badgerTree.publishRoot(root, contentHash, {"from": rootUpdater})

    assert badgerTree.getCurrentMerkleData()[0] == root
    assert badgerTree.getCurrentMerkleData()[1] == contentHash


def test_claim():
    # Generate root with single user with sample intermediate staking data

    # Add multiple tokens on second root

    # Ensure can't claim more than allowed

    assert False


def test_token_claim_limits():
    # Generate root with massive claimable
    # Ensure claim is stopped by the invariant check
    # Pause root
    # Upload fixed root
    #
    assert False


def test_token_claim_e2e():
    """
    TODO: Finish all unit tests first
    """
    # Generate realistic data using staking actions
    # Ensure expected results for each user match claimed
    assert False


def test_override_cycle():
    assert False


def test_recieve_eth(setup):
    smartTimelock = setup.smartTimelock
    deployer = setup.deployer
    team = setup.team

    ethAmount = Wei("1 ether")

    preBalances = {
        "timelock": smartTimelock.balance(),
        "deployer": deployer.balance(),
    }

    deployer.transfer(smartTimelock, ethAmount)

    postBalances = {
        "timelock": smartTimelock.balance(),
        "deployer": deployer.balance(),
    }

    assert postBalances["deployer"] <= preBalances["deployer"] - ethAmount
    assert postBalances["timelock"] == preBalances["timelock"] + ethAmount

    preBalances = {
        "team0": team[0].balance(),
        "deployer": deployer.balance(),
    }

    smartTimelock.call(deployer, ethAmount, "0x", {"from": team[0], "value": ethAmount})

    postBalances = {
        "team0": team[0].balance(),
        "deployer": deployer.balance(),
    }

    assert postBalances["deployer"] == preBalances["deployer"] + ethAmount
    assert postBalances["team0"] <= preBalances["team0"] - ethAmount
