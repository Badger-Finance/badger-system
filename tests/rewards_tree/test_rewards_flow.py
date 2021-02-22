import json
import secrets

import brownie
import pytest

from brownie import *
from helpers.constants import *
from helpers.registry import registry
from rich.console import Console

console = Console()

@pytest.fixture(scope="function", autouse="True")
def setup():
    from assistant.rewards import rewards_assistant
    return rewards_assistant


# @pytest.fixture(scope="function")
# def setup_badger(badger_tree_unit):
#     return badger_tree_unit

def random_32_bytes():
    return "0x" + secrets.token_hex(32)

# @pytest.mark.skip()
def test_rewards_flow(setup):
    rewards_assistant = setup
    badgerTree = rewards_assistant.BadgerTree
    guardian = rewards_assistant.guardian
    rootUpdater = rewards_assistant.rootUpdater

    admin, proposer, validator = accounts[:3]

    rewardsContract = admin.deploy(badgerTree)
    rewardsContract.initialize(admin, proposer, validator)

    # Propose root
    root = random_32_bytes()
    contentHash = random_32_bytes()
    startBlock = rewardsContract.lastPublishStartBlock() + 1

    # Test variations of invalid data upload and verify revert string
    with brownie.reverts("Incorrect cycle"):
        rewardsContract.proposeRoot(
            root, 
            contentHash, 
            rewardsContract.currentCycle(), 
            startBlock,
            startBlock + 1, 
            {"from": proposer}
        )
    with brownie.reverts("Incorrect cycle"):
        rewardsContract.proposeRoot(
            root, 
            contentHash, 
            rewardsContract.currentCycle() + 2, 
            startBlock,
            startBlock + 1, 
            {"from": proposer}
        )
    with brownie.reverts("Incorrect start block"):
        rewardsContract.proposeRoot(
            root, 
            contentHash, 
            rewardsContract.currentCycle() + 1, 
            rewardsContract.lastPublishStartBlock() + 2,
            startBlock + 1, 
            {"from": proposer}
        )
    with brownie.reverts("Incorrect start block"):
        rewardsContract.proposeRoot(
            root, 
            contentHash, 
            rewardsContract.currentCycle() + 1, 
            rewardsContract.lastPublishStartBlock(),
            startBlock + 1, 
            {"from": proposer}
        )

    # Ensure event
    tx = rewardsContract.proposeRoot(
        root, 
        contentHash, 
        rewardsContract.currentCycle() + 1, 
        startBlock,
        startBlock + 1, 
        {"from": proposer}
    )
    assert 'RootProposed' in tx.events.keys()

    # Approve root

    # Test variations of invalid data upload and verify revert string
    with brownie.reverts("Incorrect root"):
        rewardsContract.approveRoot(
            random_32_bytes(),
            contentHash,
            rewardsContract.currentCycle(),
            startBlock,
            startBlock + 1, 
            {"from": validator}
        )
    with brownie.reverts("Incorrect content hash"):
        rewardsContract.approveRoot(
            root,
            random_32_bytes(),
            rewardsContract.currentCycle(),
            startBlock,
            startBlock + 1, 
            {"from": validator}
        )
    with brownie.reverts("Incorrect cycle"):
        rewardsContract.approveRoot(
            root,
            contentHash,
            rewardsContract.currentCycle(),
            startBlock,
            startBlock + 1, 
            {"from": validator}
        )
    with brownie.reverts("Incorrect cycle"):
        rewardsContract.approveRoot(
            root,
            contentHash,
            rewardsContract.currentCycle() + 2,
            startBlock,
            startBlock + 1, 
            {"from": validator}
        )
    with brownie.reverts("Incorrect cycle start block"):
        rewardsContract.approveRoot(
            root,
            contentHash,
            rewardsContract.pendingCycle(),
            startBlock + 1,
            startBlock + 1, 
            {"from": validator}
        )
    with brownie.reverts("Incorrect cycle start block"):
        rewardsContract.approveRoot(
            root,
            contentHash,
            rewardsContract.pendingCycle(),
            startBlock - 1,
            startBlock + 1, 
            {"from": validator}
        )
    with brownie.reverts("Incorrect cycle end block"):
        rewardsContract.approveRoot(
            root,
            contentHash,
            rewardsContract.pendingCycle(),
            startBlock,
            startBlock + 9, 
            {"from": validator}
        )
    with brownie.reverts("Incorrect cycle end block"):
        rewardsContract.approveRoot(
            root,
            contentHash,
            rewardsContract.pendingCycle(),
            startBlock,
            startBlock + 11, 
            {"from": validator}
        )
    with brownie.reverts("Incorrect cycle end block"):
        rewardsContract.approveRoot(
            root,
            contentHash,
            rewardsContract.pendingCycle(),
            startBlock,
            startBlock, 
            {"from": validator}
        )

    # Ensure event
    tx = rewardsContract.approveRoot(
        root,
        contentHash,
        rewardsContract.pendingCycle(),
        startBlock,
        startBlock + 1, 
        {"from": validator}
    )
    assert 'RootUpdated' in tx.events.keys()

    # Claim as a user 
    startBlock = rewardsContract.lastPublishStartBlock() + 1

    # Update to new root with xSushi and FARM
    rewardsContract.proposeRoot(
        root, 
        contentHash, 
        rewardsContract.currentCycle() + 1, 
        startBlock,
        startBlock + 1, 
        {"from": proposer}
    )
    
    # Claim as user who has xSushi and FARM

    # Ensure tokens are as expected

    # Claim partial as a user 
    '''
    # Try to claim with zero tokens all around, expect failure
    startBlock = rewardsContract.lastPublishStartBlock() + 1
    endBlock = startBlock + 1
    
    blockDuration = endBlock - startBlock

    nextCycle = rewardsContract.currentCycle() + 1

    currentMerkleData = {
        "root": rewardsContract.merkleRoot(),
        "contentHash": rewardsContract.merkleContentHash(),
        "lastUpdateTime": rewardsContract.lastPublishTimestamp(),
        "blockNumber": int(rewardsContract.lastPublishBlockNumber()),
    }

    geyserRewards = []
    # metaFarmRewards = calc_harvest_meta_farm_rewards(badger, startBlock, endBlock)

    newRewards = geyserRewards
    cumulativeRewards = []

    # Take metadata from geyserRewards
    console.print("Processing to merkle tree")
    merkleTree = rewards_assistant.rewards_to_merkle_tree(
        cumulativeRewards, startBlock, endBlock, geyserRewards
    )

    # Publish data
    rootHash = hash(merkleTree["merkleRoot"])

    console.log(
        {
            "merkleRoot": merkleTree["merkleRoot"],
            "rootHash": str(rootHash),
            "startBlock": startBlock,
            "endBlock": endBlock,
            "currentContentHash": currentMerkleData["contentHash"],
        }
    )

    rewardsContract.proposeRoot(
        rootHash, 
        currentMerkleData["contentHash"], 
        rewardsContract.currentCycle() + 1, 
        startBlock,
        endBlock, 
        {"from": proposer}
    )
    rewardsContract.approveRoot(
        rootHash,
        currentMerkleData["contentHash"],
        rewardsContract.pendingCycle(),
        startBlock,
        endBlock, 
        {"from": validator}
    )
    with brownie.reverts("No tokens to claim"):
        rewardsContract.claim(
            [],
            [],
            0,
            rewardsContract.currentCycle(),
            [],
            [],
            {"from": accounts[4]}
        )
    
    assert False
    '''