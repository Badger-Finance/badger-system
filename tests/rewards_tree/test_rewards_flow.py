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


# @pytest.fixture(scope="function")
# def setup_badger(badger_tree_unit):
#     return badger_tree_unit

def random_32_bytes():
    return "0x" + secrets.token_hex(32)

# generates merkle root purely off dummy data
def internal_generate_rewards_in_range(rewards_assistant, currentMerkleData, newRewards, startBlock, endBlock, pastRewards):
    cumulativeRewards = rewards_assistant.process_cumulative_rewards(pastRewards, newRewards)

    # Take metadata from geyserRewards
    console.print("Processing to merkle tree")
    merkleTree = rewards_assistant.rewards_to_merkle_tree(
        cumulativeRewards, startBlock, endBlock, newRewards
    )

    # Publish data
    rootHash = hash(merkleTree["merkleRoot"])
    contentFileName = rewards_assistant.content_hash_to_filename(rootHash)

    console.log(
        {
            "merkleRoot": merkleTree["merkleRoot"],
            "rootHash": str(rootHash),
            "contentFile": contentFileName,
            "startBlock": startBlock,
            "endBlock": endBlock,
            "currentContentHash": currentMerkleData["contentHash"],
        }
    )

    return {
        "contentFileName": contentFileName,
        "merkleTree": merkleTree,
        "rootHash": rootHash,
    }


# @pytest.mark.skip()
def test_rewards_flow(setup):
    rewards_assistant = setup
    badgerTree = rewards_assistant.BadgerTree
    guardian = rewards_assistant.guardian
    rootUpdater = rewards_assistant.rootUpdater

    admin, proposer, validator, user = accounts[:4]

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
    rewardsContract = admin.deploy(badgerTree)
    rewardsContract.initialize(admin, proposer, validator)
    
    startBlock = rewardsContract.lastPublishStartBlock() + 1
    endBlock = startBlock + 5
    nextCycle = rewardsContract.currentCycle() + 1
    currentRoot = rewardsContract.merkleRoot()

    assert user == '0x21b42413bA931038f35e7A5224FaDb065d297Ba3' # make sure we're making claims for the correct account

    # Update to new root with xSushi and FARM
    farmClaim = 100000000000
    geyserRewards = DotMap({
        'badger_tree': rewardsContract,
        'claims': {
            "0x21b42413bA931038f35e7A5224FaDb065d297Ba3": {
                "0xa0246c9032bC3A600820415aE600c6388619A14D": farmClaim,
                "0x3472A5A71965499acd81997a54BBA8D852C6E53d": 0,
                "0x798D1bE841a82a273720CE31c822C61a67a601C3": 0
            },
            "0x0063046686E46Dc6F15918b61AE2B121458534a5": {
                "0xa0246c9032bC3A600820415aE600c6388619A14D": 100,
                "0x3472A5A71965499acd81997a54BBA8D852C6E53d": 100,
                "0x798D1bE841a82a273720CE31c822C61a67a601C3": 100
            },
            "0x33A4622B82D4c04a53e170c638B944ce27cffce3": {
                "0xa0246c9032bC3A600820415aE600c6388619A14D": 100,
                "0x3472A5A71965499acd81997a54BBA8D852C6E53d": 100,
                "0x798D1bE841a82a273720CE31c822C61a67a601C3": 100
            }
        },
        "tokens": [
            "0xa0246c9032bC3A600820415aE600c6388619A14D", #FARM
            "0x3472A5A71965499acd81997a54BBA8D852C6E53d", #badger
            "0x798D1bE841a82a273720CE31c822C61a67a601C3"  #digg
        ],
        'cycle': nextCycle
    })
    pastRewards = DotMap({
        'badger_tree': rewardsContract,
        'claims': {},
        "tokens": [
            "0xa0246c9032bC3A600820415aE600c6388619A14D", #FARM
            "0x3472A5A71965499acd81997a54BBA8D852C6E53d",
            "0x798D1bE841a82a273720CE31c822C61a67a601C3"
        ],
        'cycle': nextCycle - 1
    })

    rewards_data = internal_generate_rewards_in_range(
        rewards_assistant,
        {"contentHash": currentRoot},
        geyserRewards,
        startBlock, 
        endBlock, 
        pastRewards
    )
    print(rewards_data['merkleTree']['claims'][user]['proof'])
    rewardsContract.proposeRoot(
        rewards_data["merkleTree"]["merkleRoot"],
        rewards_data["rootHash"],
        rewards_data["merkleTree"]["cycle"],
        rewards_data["merkleTree"]["startBlock"],
        rewards_data["merkleTree"]["endBlock"],
        {"from": proposer}
    )
    rewardsContract.approveRoot(
        rewards_data["merkleTree"]["merkleRoot"],
        rewards_data["rootHash"],
        rewards_data["merkleTree"]["cycle"],
        rewards_data["merkleTree"]["startBlock"],
        rewards_data["merkleTree"]["endBlock"],
        {"from": validator}
    )
    
    # Claim as user who has xSushi and FARM
    rewardsContract.claim(
        [
            "0xa0246c9032bC3A600820415aE600c6388619A14D", #FARM
            "0x3472A5A71965499acd81997a54BBA8D852C6E53d", #badger
            "0x798D1bE841a82a273720CE31c822C61a67a601C3"  #digg
        ],
        [farmClaim, 0, 0],
        rewards_data['merkleTree']['claims'][user]['index'],
        rewards_data['merkleTree']['cycle'],
        rewards_data['merkleTree']['claims'][user]['proof'],
        [farmClaim, 0, 0],
        {"from": user}
    )

    # Ensure tokens are as expected
    farmBalance = Contract.at('0xa0246c9032bC3A600820415aE600c6388619A14D').balanceOf(user)
    assert farmClaim == farmBalance


    # Claim partial as a user 

    # Try to claim with zero tokens all around, expect failure
    rewardsContract = admin.deploy(badgerTree)
    rewardsContract.initialize(admin, proposer, validator)
    
    startBlock = rewardsContract.lastPublishStartBlock() + 1
    endBlock = startBlock + 5
    nextCycle = rewardsContract.currentCycle() + 1
    currentRoot = rewardsContract.merkleRoot()

    geyserRewards = DotMap({
        'badger_tree': rewardsContract,
        'claims': {
            "0x21b42413bA931038f35e7A5224FaDb065d297Ba3": {
                "0xa0246c9032bC3A600820415aE600c6388619A14D": 0,
                "0x3472A5A71965499acd81997a54BBA8D852C6E53d": 0,
                "0x798D1bE841a82a273720CE31c822C61a67a601C3": 0
            },
            "0x0063046686E46Dc6F15918b61AE2B121458534a5": {
                "0xa0246c9032bC3A600820415aE600c6388619A14D": 0,
                "0x3472A5A71965499acd81997a54BBA8D852C6E53d": 0,
                "0x798D1bE841a82a273720CE31c822C61a67a601C3": 0
            },
            "0x33A4622B82D4c04a53e170c638B944ce27cffce3": {
                "0xa0246c9032bC3A600820415aE600c6388619A14D": 0,
                "0x3472A5A71965499acd81997a54BBA8D852C6E53d": 0,
                "0x798D1bE841a82a273720CE31c822C61a67a601C3": 0
            }
        },
        "tokens": [
            "0xa0246c9032bC3A600820415aE600c6388619A14D", #FARM
            "0x3472A5A71965499acd81997a54BBA8D852C6E53d", #BADGER
            "0x798D1bE841a82a273720CE31c822C61a67a601C3" #DIGG
        ],
        'totals': {},
        'cycle': nextCycle,
        'metadata': {},
        'sources': {},
        'sourceMetadata': {}
    })
    pastRewards = DotMap({
        'badger_tree': rewardsContract,
        'claims': {},
        "tokens": [
            "0xa0246c9032bC3A600820415aE600c6388619A14D", #FARM
            "0x3472A5A71965499acd81997a54BBA8D852C6E53d", #BADGER
            "0x798D1bE841a82a273720CE31c822C61a67a601C3" #DIGG
        ],
        'totals': {},
        'cycle': nextCycle - 1,
        'metadata': {},
        'sources': {},
        'sourceMetadata': {}
    })

    rewards_data = internal_generate_rewards_in_range(
        rewards_assistant,
        {"contentHash": currentRoot},
        geyserRewards,
        startBlock, 
        endBlock, 
        pastRewards
    )

    rewardsContract.proposeRoot(
        rewards_data["merkleTree"]["merkleRoot"],
        rewards_data["rootHash"],
        rewards_data["merkleTree"]["cycle"],
        rewards_data["merkleTree"]["startBlock"],
        rewards_data["merkleTree"]["endBlock"],
        {"from": proposer}
    )
    rewardsContract.approveRoot(
        rewards_data["merkleTree"]["merkleRoot"],
        rewards_data["rootHash"],
        rewards_data["merkleTree"]["cycle"],
        rewards_data["merkleTree"]["startBlock"],
        rewards_data["merkleTree"]["endBlock"],
        {"from": validator}
    )
    with brownie.reverts("No tokens to claim"):
        rewardsContract.claim(
            [
                "0xa0246c9032bC3A600820415aE600c6388619A14D",
                "0x3472A5A71965499acd81997a54BBA8D852C6E53d",
                "0x798D1bE841a82a273720CE31c822C61a67a601C3"
            ],
            [0,0,0],
            0,
            rewardsContract.currentCycle(),
            [],
            [0,0,0],
            {"from": user}
        )
    
    assert False
