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

FARM_ADDRESS = "0xa0246c9032bC3A600820415aE600c6388619A14D"
XSUSHI_ADDRESS = "0x8798249c2E607446EfB7Ad49eC89dD1865Ff4272"
SECS_PER_HOUR = 3600
SECS_PER_DAY = 86400

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
def internal_generate_rewards_in_range(
    rewards_assistant, currentMerkleData, newRewards, startBlock, endBlock, pastRewards
):
    cumulativeRewards = rewards_assistant.process_cumulative_rewards(
        pastRewards, newRewards
    )

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
    badgerTree = rewards_assistant.BadgerTree
    guardian = rewards_assistant.guardian
    rootUpdater = rewards_assistant.rootUpdater

    admin, proposer, validator, user = accounts[:4]

    rewardsContract = admin.deploy(badgerTree)
    rewardsContract.initialize(admin, proposer, validator)

    # Propose root
    root = random_32_bytes()
    contentHash = random_32_bytes()
    startBlock = rewardsContract.lastPublishEndBlock() + 1

    # Test variations of invalid data upload and verify revert string
    with brownie.reverts("Incorrect cycle"):
        rewardsContract.proposeRoot(
            root,
            contentHash,
            rewardsContract.currentCycle(),
            startBlock,
            startBlock + 1,
            {"from": proposer},
        )
    with brownie.reverts("Incorrect cycle"):
        rewardsContract.proposeRoot(
            root,
            contentHash,
            rewardsContract.currentCycle() + 2,
            startBlock,
            startBlock + 1,
            {"from": proposer},
        )
    with brownie.reverts("Incorrect start block"):
        rewardsContract.proposeRoot(
            root,
            contentHash,
            rewardsContract.currentCycle() + 1,
            rewardsContract.lastPublishEndBlock() + 2,
            startBlock + 1,
            {"from": proposer},
        )
    with brownie.reverts("Incorrect start block"):
        rewardsContract.proposeRoot(
            root,
            contentHash,
            rewardsContract.currentCycle() + 1,
            rewardsContract.lastPublishEndBlock(),
            startBlock + 1,
            {"from": proposer},
        )

    # Ensure event
    tx = rewardsContract.proposeRoot(
        root,
        contentHash,
        rewardsContract.currentCycle() + 1,
        startBlock,
        startBlock + 1,
        {"from": proposer},
    )
    assert "RootProposed" in tx.events.keys()

    # Approve root

    # Test variations of invalid data upload and verify revert string
    with brownie.reverts("Incorrect root"):
        rewardsContract.approveRoot(
            random_32_bytes(),
            contentHash,
            rewardsContract.currentCycle(),
            startBlock,
            startBlock + 1,
            {"from": validator},
        )
    with brownie.reverts("Incorrect content hash"):
        rewardsContract.approveRoot(
            root,
            random_32_bytes(),
            rewardsContract.currentCycle(),
            startBlock,
            startBlock + 1,
            {"from": validator},
        )
    with brownie.reverts("Incorrect cycle"):
        rewardsContract.approveRoot(
            root,
            contentHash,
            rewardsContract.currentCycle(),
            startBlock,
            startBlock + 1,
            {"from": validator},
        )
    with brownie.reverts("Incorrect cycle"):
        rewardsContract.approveRoot(
            root,
            contentHash,
            rewardsContract.currentCycle() + 2,
            startBlock,
            startBlock + 1,
            {"from": validator},
        )
    with brownie.reverts("Incorrect cycle start block"):
        rewardsContract.approveRoot(
            root,
            contentHash,
            rewardsContract.pendingCycle(),
            startBlock + 1,
            startBlock + 1,
            {"from": validator},
        )
    with brownie.reverts("Incorrect cycle start block"):
        rewardsContract.approveRoot(
            root,
            contentHash,
            rewardsContract.pendingCycle(),
            startBlock - 1,
            startBlock + 1,
            {"from": validator},
        )
    with brownie.reverts("Incorrect cycle end block"):
        rewardsContract.approveRoot(
            root,
            contentHash,
            rewardsContract.pendingCycle(),
            startBlock,
            startBlock + 9,
            {"from": validator},
        )
    with brownie.reverts("Incorrect cycle end block"):
        rewardsContract.approveRoot(
            root,
            contentHash,
            rewardsContract.pendingCycle(),
            startBlock,
            startBlock + 11,
            {"from": validator},
        )
    with brownie.reverts("Incorrect cycle end block"):
        rewardsContract.approveRoot(
            root,
            contentHash,
            rewardsContract.pendingCycle(),
            startBlock,
            startBlock,
            {"from": validator},
        )

    # Ensure event
    tx = rewardsContract.approveRoot(
        root,
        contentHash,
        rewardsContract.pendingCycle(),
        startBlock,
        startBlock + 1,
        {"from": validator},
    )
    assert "RootUpdated" in tx.events.keys()

    with brownie.reverts("Incorrect start block"):
        rewardsContract.proposeRoot(
            root,
            contentHash,
            rewardsContract.currentCycle() + 1,
            rewardsContract.lastPublishStartBlock() + 1,
            startBlock + 1,
            {"from": proposer},
        )

    # Claim as a user
    rewardsContract = admin.deploy(badgerTree)
    rewardsContract.initialize(admin, proposer, validator)

    startBlock = rewardsContract.lastPublishEndBlock() + 1
    endBlock = startBlock + 5
    currCycle = rewardsContract.currentCycle()
    nextCycle = currCycle + 1
    currentRoot = rewardsContract.merkleRoot()

    # Update to new root with xSushi and FARM
    farmClaim = 100000000000
    xSushiClaim = 5555555555

    geyserRewards = DotMap(
        {
            "badger_tree": rewardsContract,
            "claims": {
                user.address: {FARM_ADDRESS: farmClaim, XSUSHI_ADDRESS: xSushiClaim},
                accounts[5].address: {FARM_ADDRESS: 100, XSUSHI_ADDRESS: 100},
                accounts[6].address: {FARM_ADDRESS: 100, XSUSHI_ADDRESS: 100},
            },
            "tokens": [FARM_ADDRESS, XSUSHI_ADDRESS],
            "cycle": nextCycle,
        }
    )
    pastRewards = DotMap(
        {
            "badger_tree": rewardsContract,
            "claims": {},
            "tokens": [FARM_ADDRESS, XSUSHI_ADDRESS],
            "cycle": currCycle,
        }
    )

    rewards_data = internal_generate_rewards_in_range(
        rewards_assistant,
        {"contentHash": currentRoot},
        geyserRewards,
        startBlock,
        endBlock,
        pastRewards,
    )

    rewardsContract.proposeRoot(
        rewards_data["merkleTree"]["merkleRoot"],
        rewards_data["rootHash"],
        rewards_data["merkleTree"]["cycle"],
        rewards_data["merkleTree"]["startBlock"],
        rewards_data["merkleTree"]["endBlock"],
        {"from": proposer},
    )
    rewardsContract.approveRoot(
        rewards_data["merkleTree"]["merkleRoot"],
        rewards_data["rootHash"],
        rewards_data["merkleTree"]["cycle"],
        rewards_data["merkleTree"]["startBlock"],
        rewards_data["merkleTree"]["endBlock"],
        {"from": validator},
    )

    # Claim as user who has xSushi and FARM

    # This revert message means the claim was valid and it tried to transfer rewards
    # it can't actually transfer any with this setup
    with brownie.reverts("ERC20: transfer amount exceeds balance"):
        rewardsContract.claim(
            [FARM_ADDRESS, XSUSHI_ADDRESS],  # FARM  # XSUSHI
            [farmClaim, xSushiClaim],
            rewards_data["merkleTree"]["claims"][user]["index"],
            rewards_data["merkleTree"]["cycle"],
            rewards_data["merkleTree"]["claims"][user]["proof"],
            [farmClaim, xSushiClaim],
            {"from": user},
        )

    # Ensure tokens are as expected
    # farmBalance = Contract.at("0xa0246c9032bC3A600820415aE600c6388619A14D").balanceOf(user)
    # assert farmClaim == farmBalance

    # Claim partial as a user
    with brownie.reverts("ERC20: transfer amount exceeds balance"):
        rewardsContract.claim(
            [FARM_ADDRESS, XSUSHI_ADDRESS],
            [farmClaim, xSushiClaim],
            rewards_data["merkleTree"]["claims"][user]["index"],
            rewards_data["merkleTree"]["cycle"],
            rewards_data["merkleTree"]["claims"][user]["proof"],
            [farmClaim - 100, xSushiClaim - 100],
            {"from": user},
        )

    # Claim with MockToken and confirm new balance
    mockToken = rewards_assistant.MockToken
    mockContract = admin.deploy(mockToken)
    mockContract.initialize([rewardsContract], [100000000])

    startBlock = rewardsContract.lastPublishEndBlock() + 1
    endBlock = startBlock + 5
    currCycle = rewardsContract.currentCycle()
    nextCycle = currCycle + 1
    currentRoot = rewardsContract.merkleRoot()

    geyserRewards = DotMap(
        {
            "badger_tree": rewardsContract,
            "claims": {
                user.address: {},
                accounts[5].address: {},
                accounts[6].address: {},
            },
            "tokens": [mockContract],
            "cycle": nextCycle,
        }
    )
    geyserRewards["claims"][user.address][str(mockContract)] = 100
    geyserRewards["claims"][accounts[5].address][str(mockContract)] = 20
    geyserRewards["claims"][accounts[6].address][str(mockContract)] = 0
    pastRewards = DotMap(
        {
            "badger_tree": rewardsContract,
            "claims": {},
            "tokens": [mockContract],
            "cycle": currCycle,
        }
    )

    rewards_data = internal_generate_rewards_in_range(
        rewards_assistant,
        {"contentHash": currentRoot},
        geyserRewards,
        startBlock,
        endBlock,
        pastRewards,
    )

    rewardsContract.proposeRoot(
        rewards_data["merkleTree"]["merkleRoot"],
        rewards_data["rootHash"],
        rewards_data["merkleTree"]["cycle"],
        rewards_data["merkleTree"]["startBlock"],
        rewards_data["merkleTree"]["endBlock"],
        {"from": proposer},
    )
    rewardsContract.approveRoot(
        rewards_data["merkleTree"]["merkleRoot"],
        rewards_data["rootHash"],
        rewards_data["merkleTree"]["cycle"],
        rewards_data["merkleTree"]["startBlock"],
        rewards_data["merkleTree"]["endBlock"],
        {"from": validator},
    )

    rewardsContract.claim(
        [mockContract],
        [100],
        rewards_data["merkleTree"]["claims"][user]["index"],
        rewards_data["merkleTree"]["cycle"],
        rewards_data["merkleTree"]["claims"][user]["proof"],
        [100],
        {"from": user},
    )

    assert mockContract.balanceOf(user) == 100
    assert mockContract.balanceOf(str(rewardsContract)) == 100000000 - 100

    # Try to claim with zero tokens all around, expect failure
    rewardsContract = admin.deploy(badgerTree)
    rewardsContract.initialize(admin, proposer, validator)

    startBlock = rewardsContract.lastPublishEndBlock() + 1
    endBlock = startBlock + 5
    currCycle = rewardsContract.currentCycle()
    nextCycle = currCycle + 1
    currentRoot = rewardsContract.merkleRoot()

    geyserRewards = DotMap(
        {
            "badger_tree": rewardsContract,
            "claims": {
                user.address: {FARM_ADDRESS: 0, XSUSHI_ADDRESS: 0},
                accounts[5].address: {FARM_ADDRESS: 0, XSUSHI_ADDRESS: 0},
                accounts[6].address: {FARM_ADDRESS: 0, XSUSHI_ADDRESS: 0},
            },
            "tokens": [FARM_ADDRESS, XSUSHI_ADDRESS],  # FARM  # XSUSHI
            "cycle": nextCycle,
        }
    )
    pastRewards = DotMap(
        {
            "badger_tree": rewardsContract,
            "claims": {},
            "tokens": [FARM_ADDRESS, XSUSHI_ADDRESS],  # FARM  # XSUSHI
            "cycle": currCycle,
        }
    )

    rewards_data = internal_generate_rewards_in_range(
        rewards_assistant,
        {"contentHash": currentRoot},
        geyserRewards,
        startBlock,
        endBlock,
        pastRewards,
    )

    rewardsContract.proposeRoot(
        rewards_data["merkleTree"]["merkleRoot"],
        rewards_data["rootHash"],
        rewards_data["merkleTree"]["cycle"],
        rewards_data["merkleTree"]["startBlock"],
        rewards_data["merkleTree"]["endBlock"],
        {"from": proposer},
    )
    rewardsContract.approveRoot(
        rewards_data["merkleTree"]["merkleRoot"],
        rewards_data["rootHash"],
        rewards_data["merkleTree"]["cycle"],
        rewards_data["merkleTree"]["startBlock"],
        rewards_data["merkleTree"]["endBlock"],
        {"from": validator},
    )

    with brownie.reverts("No tokens to claim"):
        rewardsContract.claim(
            [FARM_ADDRESS, XSUSHI_ADDRESS],  # FARM  # XSUSHI
            [0, 0],
            rewards_data["merkleTree"]["claims"][user]["index"],
            rewards_data["merkleTree"]["cycle"],
            rewards_data["merkleTree"]["claims"][user]["proof"],
            [0, 0],
            {"from": user},
        )


def test_salary(setup):
    rewards_assistant = setup

    admin, proposer, validator = accounts[:3]
    users = accounts[3:]

    rewards_contract = admin.deploy(rewards_assistant.BadgerTree)
    rewards_contract.initialize(admin, proposer, validator)

    def make_salary_entry(recipient, token, total_amount, duration, start_time):
        return DotMap(
            {
                "recipient": recipient,
                "token": token,
                "totalAmount": total_amount,
                "duration": duration,
                "startTime": start_time,
                "endTime": start_time + duration,
            }
        )

    def update_root(rewards_data):
        rewards_contract.proposeRoot(
            rewards_data["merkleTree"]["merkleRoot"],
            rewards_data["rootHash"],
            rewards_data["merkleTree"]["cycle"],
            rewards_data["merkleTree"]["startBlock"],
            rewards_data["merkleTree"]["endBlock"],
            {"from": proposer},
        )
        rewards_contract.approveRoot(
            rewards_data["merkleTree"]["merkleRoot"],
            rewards_data["rootHash"],
            rewards_data["merkleTree"]["cycle"],
            rewards_data["merkleTree"]["startBlock"],
            rewards_data["merkleTree"]["endBlock"],
            {"from": validator},
        )

    def calculate_payment(salary_entry, start_block_time, end_block_time):
        print(
            f"salary_entry: {salary_entry}\nstart_block_time:\t{start_block_time}\nend_block_time:  \t{end_block_time}"
        )
        if (
            salary_entry.startTime <= end_block_time
            and salary_entry.endTime > start_block_time
        ):
            start_time = max(salary_entry.startTime, start_block_time)
            end_time = min(salary_entry.endTime, end_block_time)
            return (
                salary_entry.totalAmount
                * salary_entry.duration
                / (end_time - start_time)
            )
        return 0

    mock_token = rewards_assistant.MockToken
    mock_contract = admin.deploy(mock_token)
    mock_contract.initialize([rewards_contract], [10_000_000_000_000_000_000_000_000])

    salaries = [
        make_salary_entry(
            users[0].address,
            mock_contract,
            1_000_000_000_000_000_000,
            SECS_PER_DAY * 360,
            chain.time() - SECS_PER_DAY * 30,
        ),
        make_salary_entry(
            users[1].address,
            mock_contract,
            1_000_000_000_000_000_000,
            SECS_PER_DAY * 180,
            chain.time() - SECS_PER_DAY * 200,
        ),
        make_salary_entry(
            users[2].address,
            mock_contract,
            1_000_000_000_000_000_000,
            SECS_PER_DAY * 180,
            chain.time() + SECS_PER_DAY * 30,
        ),
        make_salary_entry(
            users[3].address,
            mock_contract,
            1_000_000_000_000_000_000,
            SECS_PER_DAY * 180,
            chain.time() + SECS_PER_HOUR * 2,
        ),
    ]

    void_state = DotMap(
        {
            "badger_tree": rewards_contract,
            "claims": {},
            "tokens": [mock_contract.address],
            "cycle": rewards_contract.currentCycle(),
        }
    )
    initial_state = DotMap(
        {
            "badger_tree": rewards_contract,
            "claims": {users[20].address: {mock_contract.address: 456}},
            "tokens": [mock_contract.address],
            "cycle": rewards_contract.currentCycle() + 1,
        }
    )

    update_root(
        internal_generate_rewards_in_range(
            rewards_assistant,
            {"contentHash": rewards_contract.merkleRoot()},
            initial_state,
            rewards_contract.lastPublishEndBlock() + 1,
            web3.eth.blockNumber,
            void_state,
        )
    )

    sleep_time = SECS_PER_HOUR * 4
    chain.sleep(sleep_time)
    chain.mine(50)

    last_publish_time = rewards_contract.lastPublishTimestamp()
    chain_time = chain.time()

    claims = {
        entry.recipient: {
            mock_contract.address: calculate_payment(
                entry, rewards_contract.lastPublishTimestamp(), chain.time()
            )
        }
        for entry in salaries
    }

    assert claims[users[0]][mock_contract.address] > 0
    assert claims[users[1]][mock_contract.address] == 0
    assert claims[users[2]][mock_contract.address] == 0
    assert claims[users[3]][mock_contract.address] > 0

    update_state = DotMap(
        {
            "badger_tree": rewards_contract,
            "claims": claims,
            "tokens": [mock_contract],
            "cycle": rewards_contract.currentCycle() + 1,
        }
    )

    rewards_data = internal_generate_rewards_in_range(
        rewards_assistant,
        {"contentHash": rewards_contract.merkleRoot()},
        update_state,
        rewards_contract.lastPublishEndBlock() + 1,
        web3.eth.blockNumber,
        initial_state,
    )
    console.log(rewards_data)
    update_root(rewards_data)

    # TODO: Do something more than just verify that the above change was made
    entry1 = salaries[0]
    rewards_contract.claim(
        [mock_contract],
        [claims[entry1.recipient][mock_contract.address]],
        rewards_data["merkleTree"]["claims"][entry1.recipient]["index"],
        rewards_data["merkleTree"]["cycle"],
        rewards_data["merkleTree"]["claims"][entry1.recipient]["proof"],
        [calculate_payment(entry1, last_publish_time, chain_time)],
        {"from": entry1.recipient},
    )
