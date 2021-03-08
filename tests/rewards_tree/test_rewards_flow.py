import secrets
from types import ModuleType
from typing import Any

import brownie
import pytest
from brownie.network.contract import ProjectContract
from dotmap import DotMap
from rich.console import Console

from helpers.constants import *

FARM_ADDRESS = "0xa0246c9032bC3A600820415aE600c6388619A14D"
XSUSHI_ADDRESS = "0x8798249c2E607446EfB7Ad49eC89dD1865Ff4272"
SECS_PER_HOUR = 3600
SECS_PER_DAY = 86400

console = Console()


@pytest.fixture(scope="function", autouse=True)
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
        rewards_assistant: ModuleType('rewards_assistant'),
        contract: ProjectContract,
        new_rewards: dict[str, Any],
        start_block: int,
        end_block: int,
        past_rewards: dict[str, Any]
) -> dict[str, Any]:
    cumulative_rewards = rewards_assistant.process_cumulative_rewards(past_rewards, new_rewards)

    # Take metadata from geyserRewards
    console.print("Processing to merkle tree")
    merkle_tree = rewards_assistant.rewards_to_merkle_tree(
        cumulative_rewards, start_block, end_block, new_rewards
    )

    # Publish data
    root_hash = rewards_assistant.hash(merkle_tree["merkleRoot"])
    content_file_name = rewards_assistant.content_hash_to_filename(root_hash)

    console.log(
        {
            "merkleRoot": merkle_tree["merkleRoot"],
            "rootHash": str(root_hash),
            "contentFile": content_file_name,
            "startBlock": start_block,
            "endBlock": end_block,
            "currentContentHash": contract.merkleRoot(),
        }
    )

    return {
        "contentFileName": content_file_name,
        "merkleTree": merkle_tree,
        "rootHash": root_hash,
    }


# @pytest.mark.skip()
def test_rewards_flow(setup: ModuleType('rewards_assistant')):
    rewards_assistant = setup
    badger_tree = rewards_assistant.BadgerTree

    admin, proposer, validator, user = accounts[:4]

    rewards_contract = admin.deploy(badger_tree)
    rewards_contract.initialize(admin, proposer, validator)

    # Propose root
    root = random_32_bytes()
    content_hash = random_32_bytes()
    start_block = rewards_contract.lastPublishEndBlock() + 1

    # Test variations of invalid data upload and verify revert string
    with brownie.reverts("Incorrect cycle"):
        rewards_contract.proposeRoot(
            root,
            content_hash,
            rewards_contract.currentCycle(),
            start_block,
            start_block + 1,
            {"from": proposer}
        )
    with brownie.reverts("Incorrect cycle"):
        rewards_contract.proposeRoot(
            root,
            content_hash,
            rewards_contract.currentCycle() + 2,
            start_block,
            start_block + 1,
            {"from": proposer}
        )
    with brownie.reverts("Incorrect start block"):
        rewards_contract.proposeRoot(
            root,
            content_hash,
            rewards_contract.currentCycle() + 1,
            rewards_contract.lastPublishEndBlock() + 2,
            start_block + 1,
            {"from": proposer}
        )
    with brownie.reverts("Incorrect start block"):
        rewards_contract.proposeRoot(
            root,
            content_hash,
            rewards_contract.currentCycle() + 1,
            rewards_contract.lastPublishEndBlock(),
            start_block + 1,
            {"from": proposer}
        )

    # Ensure event
    tx = rewards_contract.proposeRoot(
        root,
        content_hash,
        rewards_contract.currentCycle() + 1,
        start_block,
        start_block + 1,
        {"from": proposer}
    )
    assert "RootProposed" in tx.events.keys()

    # Approve root

    # Test variations of invalid data upload and verify revert string
    with brownie.reverts("Incorrect root"):
        rewards_contract.approveRoot(
            random_32_bytes(),
            content_hash,
            rewards_contract.currentCycle(),
            start_block,
            start_block + 1,
            {"from": validator}
        )
    with brownie.reverts("Incorrect content hash"):
        rewards_contract.approveRoot(
            root,
            random_32_bytes(),
            rewards_contract.currentCycle(),
            start_block,
            start_block + 1,
            {"from": validator}
        )
    with brownie.reverts("Incorrect cycle"):
        rewards_contract.approveRoot(
            root,
            content_hash,
            rewards_contract.currentCycle(),
            start_block,
            start_block + 1,
            {"from": validator}
        )
    with brownie.reverts("Incorrect cycle"):
        rewards_contract.approveRoot(
            root,
            content_hash,
            rewards_contract.currentCycle() + 2,
            start_block,
            start_block + 1,
            {"from": validator}
        )
    with brownie.reverts("Incorrect cycle start block"):
        rewards_contract.approveRoot(
            root,
            content_hash,
            rewards_contract.pendingCycle(),
            start_block + 1,
            start_block + 1,
            {"from": validator}
        )
    with brownie.reverts("Incorrect cycle start block"):
        rewards_contract.approveRoot(
            root,
            content_hash,
            rewards_contract.pendingCycle(),
            start_block - 1,
            start_block + 1,
            {"from": validator}
        )
    with brownie.reverts("Incorrect cycle end block"):
        rewards_contract.approveRoot(
            root,
            content_hash,
            rewards_contract.pendingCycle(),
            start_block,
            start_block + 9,
            {"from": validator}
        )
    with brownie.reverts("Incorrect cycle end block"):
        rewards_contract.approveRoot(
            root,
            content_hash,
            rewards_contract.pendingCycle(),
            start_block,
            start_block + 11,
            {"from": validator}
        )
    with brownie.reverts("Incorrect cycle end block"):
        rewards_contract.approveRoot(
            root,
            content_hash,
            rewards_contract.pendingCycle(),
            start_block,
            start_block,
            {"from": validator}
        )

    # Ensure event
    tx = rewards_contract.approveRoot(
        root,
        content_hash,
        rewards_contract.pendingCycle(),
        start_block,
        start_block + 1,
        {"from": validator}
    )
    assert "RootUpdated" in tx.events.keys()

    with brownie.reverts("Incorrect start block"):
        rewards_contract.proposeRoot(
            root,
            content_hash,
            rewards_contract.currentCycle() + 1,
            rewards_contract.lastPublishStartBlock() + 1,
            start_block + 1,
            {"from": proposer}
        )

    # Claim as a user
    rewards_contract = admin.deploy(badger_tree)
    rewards_contract.initialize(admin, proposer, validator)

    start_block = rewards_contract.lastPublishEndBlock() + 1
    end_block = start_block + 5
    curr_cycle = rewards_contract.currentCycle()
    next_cycle = curr_cycle + 1

    # Update to new root with xSushi and FARM
    farm_claim = 100000000000
    xsushi_claim = 5555555555

    geyser_rewards = DotMap({
        "badger_tree": rewards_contract,
        "claims": {
            user.address: {
                FARM_ADDRESS: farm_claim,
                XSUSHI_ADDRESS: xsushi_claim
            },
            accounts[5].address: {
                FARM_ADDRESS: 100,
                XSUSHI_ADDRESS: 100
            },
            accounts[6].address: {
                FARM_ADDRESS: 100,
                XSUSHI_ADDRESS: 100
            }
        },
        "tokens": [
            FARM_ADDRESS,
            XSUSHI_ADDRESS
        ],
        "cycle": next_cycle
    })
    past_rewards = DotMap({
        "badger_tree": rewards_contract,
        "claims": {},
        "tokens": [
            FARM_ADDRESS,
            XSUSHI_ADDRESS
        ],
        "cycle": curr_cycle
    })

    rewards_data = internal_generate_rewards_in_range(
        rewards_assistant,
        rewards_contract,
        geyser_rewards,
        start_block,
        end_block,
        past_rewards
    )

    rewards_contract.proposeRoot(
        rewards_data["merkleTree"]["merkleRoot"],
        rewards_data["rootHash"],
        rewards_data["merkleTree"]["cycle"],
        rewards_data["merkleTree"]["startBlock"],
        rewards_data["merkleTree"]["endBlock"],
        {"from": proposer}
    )
    rewards_contract.approveRoot(
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
    with brownie.reverts("ERC20: transfer amount exceeds balance"):
        rewards_contract.claim(
            [
                FARM_ADDRESS,  # FARM
                XSUSHI_ADDRESS  # XSUSHI
            ],
            [farm_claim, xsushi_claim],
            rewards_data["merkleTree"]["claims"][user]["index"],
            rewards_data["merkleTree"]["cycle"],
            rewards_data["merkleTree"]["claims"][user]["proof"],
            [farm_claim, xsushi_claim],
            {"from": user}
        )

    # Ensure tokens are as expected
    # farmBalance = Contract.at("0xa0246c9032bC3A600820415aE600c6388619A14D").balanceOf(user)
    # assert farmClaim == farmBalance

    # Claim partial as a user
    with brownie.reverts("ERC20: transfer amount exceeds balance"):
        rewards_contract.claim(
            [FARM_ADDRESS, XSUSHI_ADDRESS],
            [farm_claim, xsushi_claim],
            rewards_data["merkleTree"]["claims"][user]["index"],
            rewards_data["merkleTree"]["cycle"],
            rewards_data["merkleTree"]["claims"][user]["proof"],
            [farm_claim - 100, xsushi_claim - 100],
            {"from": user}
        )

    # Claim with MockToken and confirm new balance
    mock_token = rewards_assistant.MockToken
    mock_contract = admin.deploy(mock_token)
    mock_contract.initialize([rewards_contract], [100000000])

    start_block = rewards_contract.lastPublishEndBlock() + 1
    end_block = start_block + 5
    curr_cycle = rewards_contract.currentCycle()
    next_cycle = curr_cycle + 1

    geyser_rewards = DotMap({
        "badger_tree": rewards_contract,
        "claims": {
            user.address: {},
            accounts[5].address: {},
            accounts[6].address: {}
        },
        "tokens": [
            mock_contract
        ],
        "cycle": next_cycle
    })
    geyser_rewards["claims"][user.address][str(mock_contract)] = 100
    geyser_rewards["claims"][accounts[5].address][str(mock_contract)] = 20
    geyser_rewards["claims"][accounts[6].address][str(mock_contract)] = 0
    past_rewards = DotMap({
        "badger_tree": rewards_contract,
        "claims": {},
        "tokens": [
            mock_contract
        ],
        "cycle": curr_cycle
    })

    rewards_data = internal_generate_rewards_in_range(
        rewards_assistant,
        rewards_contract,
        geyser_rewards,
        start_block,
        end_block,
        past_rewards
    )

    rewards_contract.proposeRoot(
        rewards_data["merkleTree"]["merkleRoot"],
        rewards_data["rootHash"],
        rewards_data["merkleTree"]["cycle"],
        rewards_data["merkleTree"]["startBlock"],
        rewards_data["merkleTree"]["endBlock"],
        {"from": proposer}
    )
    rewards_contract.approveRoot(
        rewards_data["merkleTree"]["merkleRoot"],
        rewards_data["rootHash"],
        rewards_data["merkleTree"]["cycle"],
        rewards_data["merkleTree"]["startBlock"],
        rewards_data["merkleTree"]["endBlock"],
        {"from": validator}
    )

    rewards_contract.claim(
        [mock_contract],
        [100],
        rewards_data["merkleTree"]["claims"][user]["index"],
        rewards_data["merkleTree"]["cycle"],
        rewards_data["merkleTree"]["claims"][user]["proof"],
        [100],
        {"from": user}
    )

    assert mock_contract.balanceOf(user) == 100
    assert mock_contract.balanceOf(str(rewards_contract)) == 100000000 - 100

    # Try to claim with zero tokens all around, expect failure
    rewards_contract = admin.deploy(badger_tree)
    rewards_contract.initialize(admin, proposer, validator)

    start_block = rewards_contract.lastPublishEndBlock() + 1
    end_block = start_block + 5
    curr_cycle = rewards_contract.currentCycle()
    next_cycle = curr_cycle + 1

    geyser_rewards = DotMap({
        "badger_tree": rewards_contract,
        "claims": {
            user.address: {
                FARM_ADDRESS: 0,
                XSUSHI_ADDRESS: 0
            },
            accounts[5].address: {
                FARM_ADDRESS: 0,
                XSUSHI_ADDRESS: 0
            },
            accounts[6].address: {
                FARM_ADDRESS: 0,
                XSUSHI_ADDRESS: 0
            }
        },
        "tokens": [
            FARM_ADDRESS,  # FARM
            XSUSHI_ADDRESS  # XSUSHI
        ],
        "cycle": next_cycle
    })
    past_rewards = DotMap({
        "badger_tree": rewards_contract,
        "claims": {},
        "tokens": [
            FARM_ADDRESS,  # FARM
            XSUSHI_ADDRESS  # XSUSHI
        ],
        "cycle": curr_cycle
    })

    rewards_data = internal_generate_rewards_in_range(
        rewards_assistant,
        rewards_contract,
        geyser_rewards,
        start_block,
        end_block,
        past_rewards
    )

    rewards_contract.proposeRoot(
        rewards_data["merkleTree"]["merkleRoot"],
        rewards_data["rootHash"],
        rewards_data["merkleTree"]["cycle"],
        rewards_data["merkleTree"]["startBlock"],
        rewards_data["merkleTree"]["endBlock"],
        {"from": proposer}
    )
    rewards_contract.approveRoot(
        rewards_data["merkleTree"]["merkleRoot"],
        rewards_data["rootHash"],
        rewards_data["merkleTree"]["cycle"],
        rewards_data["merkleTree"]["startBlock"],
        rewards_data["merkleTree"]["endBlock"],
        {"from": validator}
    )

    with brownie.reverts("No tokens to claim"):
        rewards_contract.claim(
            [
                FARM_ADDRESS,  # FARM
                XSUSHI_ADDRESS  # XSUSHI
            ],
            [0, 0],
            rewards_data["merkleTree"]["claims"][user]["index"],
            rewards_data["merkleTree"]["cycle"],
            rewards_data["merkleTree"]["claims"][user]["proof"],
            [0, 0],
            {"from": user}
        )


def test_salary(setup: ModuleType('rewards_assistant')):
    rewards_assistant = setup

    admin, proposer, validator = accounts[:3]
    users = accounts[3:]

    rewards_contract = admin.deploy(rewards_assistant.BadgerTree)
    rewards_contract.initialize(admin, proposer, validator)

    def make_salary_entry(
            recipient: str,
            token: ProjectContract,
            total_amount: int,
            duration: int,
            start_time: int
    ) -> DotMap[str, Any]:
        return DotMap({
            "recipient": recipient,
            "token": token,
            "totalAmount": total_amount,
            "duration": duration,
            "startTime": start_time,
            "endTime": start_time + duration
        })

    def update_root(new_rewards_data: dict[str, Any]):
        rewards_contract.proposeRoot(
            new_rewards_data["merkleTree"]["merkleRoot"],
            new_rewards_data["rootHash"],
            new_rewards_data["merkleTree"]["cycle"],
            new_rewards_data["merkleTree"]["startBlock"],
            new_rewards_data["merkleTree"]["endBlock"],
            {"from": proposer}
        )
        rewards_contract.approveRoot(
            new_rewards_data["merkleTree"]["merkleRoot"],
            new_rewards_data["rootHash"],
            new_rewards_data["merkleTree"]["cycle"],
            new_rewards_data["merkleTree"]["startBlock"],
            new_rewards_data["merkleTree"]["endBlock"],
            {"from": validator}
        )

    def calculate_payment(salary_entry: DotMap[str, Any], start_block_time: int, end_block_time: int) -> int:
        print(
            f"salary_entry: {salary_entry}\nstart_block_time:\t{start_block_time}\nend_block_time:  \t{end_block_time}")
        if salary_entry.startTime <= end_block_time and salary_entry.endTime > start_block_time:
            start_time = max(salary_entry.startTime, start_block_time)
            end_time = min(salary_entry.endTime, end_block_time)
            return salary_entry.totalAmount * salary_entry.duration / (end_time - start_time)
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
            chain.time() - SECS_PER_DAY * 30
        ),
        make_salary_entry(
            users[1].address,
            mock_contract,
            1_000_000_000_000_000_000,
            SECS_PER_DAY * 180,
            chain.time() - SECS_PER_DAY * 200
        ),
        make_salary_entry(
            users[2].address,
            mock_contract,
            1_000_000_000_000_000_000,
            SECS_PER_DAY * 180,
            chain.time() + SECS_PER_DAY * 30
        ),
        make_salary_entry(
            users[3].address,
            mock_contract,
            1_000_000_000_000_000_000,
            SECS_PER_DAY * 180,
            chain.time() + SECS_PER_HOUR * 2
        )
    ]

    void_state = DotMap({
        "badger_tree": rewards_contract,
        "claims": {},
        "tokens": [mock_contract.address],
        "cycle": rewards_contract.currentCycle()
    })
    initial_state = DotMap({
        "badger_tree": rewards_contract,
        "claims": {
            users[20].address: {mock_contract.address: 456}
        },
        "tokens": [mock_contract.address],
        "cycle": rewards_contract.currentCycle() + 1
    })

    update_root(internal_generate_rewards_in_range(
        rewards_assistant,
        rewards_contract,
        initial_state,
        rewards_contract.lastPublishEndBlock() + 1,
        web3.eth.blockNumber,
        void_state
    ))

    sleep_time = SECS_PER_HOUR * 4
    chain.sleep(sleep_time)
    chain.mine(50)

    last_publish_time = rewards_contract.lastPublishTimestamp()
    chain_time = chain.time()

    claims = {entry.recipient: {
        mock_contract.address: calculate_payment(entry, rewards_contract.lastPublishTimestamp(), chain.time())
    } for entry in salaries}

    assert claims[users[0]][mock_contract.address] > 0
    assert claims[users[1]][mock_contract.address] == 0
    assert claims[users[2]][mock_contract.address] == 0
    assert claims[users[3]][mock_contract.address] > 0

    update_state = DotMap({
        "badger_tree": rewards_contract,
        "claims": claims,
        "tokens": [mock_contract],
        "cycle": rewards_contract.currentCycle() + 1
    })

    rewards_data = internal_generate_rewards_in_range(
        rewards_assistant,
        rewards_contract,
        update_state,
        rewards_contract.lastPublishEndBlock() + 1,
        web3.eth.blockNumber,
        initial_state
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
        {"from": entry1.recipient}
    )
