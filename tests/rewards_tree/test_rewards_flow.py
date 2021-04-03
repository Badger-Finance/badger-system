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
    rootHash = rewards_assistant.hash(merkleTree["merkleRoot"])
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
    # badgerTree = rewards_assistant.BadgerTree
    badgerTree = BadgerTreeV2
    guardian = rewards_assistant.guardian
    rootUpdater = rewards_assistant.rootUpdater

    admin, proposer, validator, user = accounts[:4]

    rewardsContract = admin.deploy(BadgerTreeV2)
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
    currCycle = rewardsContract.currentCycle()
    nextCycle = currCycle + 1
    currentRoot = rewardsContract.merkleRoot()

    # Update to new root with xSushi and FARM
    farmClaim = 100000000000
    xSushiClaim = 5555555555
    farmAddress = "0xa0246c9032bC3A600820415aE600c6388619A14D"
    xSushiAddress = "0x8798249c2E607446EfB7Ad49eC89dD1865Ff4272"

    geyserRewards = DotMap({
        'badger_tree': rewardsContract,
        'claims': {
            user.address: {
                farmAddress: farmClaim,
                xSushiAddress: xSushiClaim
            },
            accounts[5].address: {
                farmAddress: 100,
                xSushiAddress: 100
            },
            accounts[6].address: {
                farmAddress: 100,
                xSushiAddress: 100
            }
        },
        "tokens": [
            farmAddress, #FARM
            xSushiAddress #XSUSHI
        ],
        'cycle': nextCycle
    })
    pastRewards = DotMap({
        'badger_tree': rewardsContract,
        'claims': {},
        "tokens": [
            farmAddress, #FARM
            xSushiAddress #XSUSHI
        ],
        'cycle': currCycle
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

    # Claim as user who has xSushi and FARM

    # This revert message means the claim was valid and it tried to transfer rewards
    # it can't actually transfer any with this setup 
    with brownie.reverts('ERC20: transfer amount exceeds balance'):
        rewardsContract.claim(
            [
                farmAddress, #FARM
                xSushiAddress #XSUSHI
            ],
            [farmClaim, xSushiClaim],
            rewards_data['merkleTree']['claims'][user]['index'],
            rewards_data['merkleTree']['cycle'],
            rewards_data['merkleTree']['claims'][user]['proof'],
            [farmClaim, xSushiClaim],
            {"from": user}
        )

    # Ensure tokens are as expected
    # farmBalance = Contract.at('0xa0246c9032bC3A600820415aE600c6388619A14D').balanceOf(user)
    # assert farmClaim == farmBalance

    # Claim partial as a user 
    with brownie.reverts('ERC20: transfer amount exceeds balance'):
        rewardsContract.claim(
            [
                farmAddress, #FARM
                xSushiAddress #XSUSHI
            ],
            [farmClaim, xSushiClaim],
            rewards_data['merkleTree']['claims'][user]['index'],
            rewards_data['merkleTree']['cycle'],
            rewards_data['merkleTree']['claims'][user]['proof'],
            [farmClaim - 100, xSushiClaim - 100],
            {"from": user}
        )

    # Claim with MockToken and confirm new balance
    mockToken = rewards_assistant.MockToken
    mockContract = admin.deploy(mockToken)
    mockContract.initialize([rewardsContract], [100000000])

    startBlock = rewardsContract.lastPublishStartBlock() + 1
    endBlock = startBlock + 5
    currCycle = rewardsContract.currentCycle()
    nextCycle = currCycle + 1
    currentRoot = rewardsContract.merkleRoot()

    geyserRewards = DotMap({
        'badger_tree': rewardsContract,
        'claims': {
            user.address: {},
            accounts[5].address: {},
            accounts[6].address: {}
        },
        "tokens": [
            mockContract
        ],
        'cycle': nextCycle
    })
    geyserRewards['claims'][user.address][str(mockContract)] = 100
    geyserRewards['claims'][accounts[5].address][str(mockContract)] = 20
    geyserRewards['claims'][accounts[6].address][str(mockContract)] = 0
    pastRewards = DotMap({
        'badger_tree': rewardsContract,
        'claims': {},
        "tokens": [
            mockContract
        ],
        'cycle': currCycle
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

    rewardsContract.claim(
        [mockContract],
        [100],
        rewards_data['merkleTree']['claims'][user]['index'],
        rewards_data['merkleTree']['cycle'],
        rewards_data['merkleTree']['claims'][user]['proof'],
        [100],
        {"from": user}
    )

    assert mockContract.balanceOf(user) == 100
    assert mockContract.balanceOf(str(rewardsContract)) == 100000000 - 100

    # Try to claim with zero tokens all around, expect failure
    rewardsContract = admin.deploy(badgerTree)
    rewardsContract.initialize(admin, proposer, validator)
    
    startBlock = rewardsContract.lastPublishStartBlock() + 1
    endBlock = startBlock + 5
    currCycle = rewardsContract.currentCycle()
    nextCycle = currCycle + 1
    currentRoot = rewardsContract.merkleRoot()

    geyserRewards = DotMap({
        'badger_tree': rewardsContract,
        'claims': {
            user.address: {
                farmAddress: 0,
                xSushiAddress: 0
            },
            accounts[5].address: {
                farmAddress: 0,
                xSushiAddress: 0
            },
            accounts[6].address: {
                farmAddress: 0,
                xSushiAddress: 0
            }
        },
        "tokens": [
            farmAddress, #FARM
            xSushiAddress #XSUSHI
        ],
        'cycle': nextCycle
    })
    pastRewards = DotMap({
        'badger_tree': rewardsContract,
        'claims': {},
        "tokens": [
            farmAddress, #FARM
            xSushiAddress #XSUSHI
        ],
        'cycle': currCycle
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
                farmAddress, #FARM
                xSushiAddress #XSUSHI
            ],
            [0, 0],
            rewards_data['merkleTree']['claims'][user]['index'],
            rewards_data['merkleTree']['cycle'],
            rewards_data['merkleTree']['claims'][user]['proof'],
            [0, 0],
            {"from": user}
        )
