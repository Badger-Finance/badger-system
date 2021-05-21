import json
import secrets

import brownie
from dotmap import DotMap
import pytest
from decimal import Decimal

import pprint

from brownie import *
from helpers.constants import *
from helpers.registry import registry
from rich.console import Console
from tests.helpers import distribute_from_whales

console = Console()


@pytest.fixture(scope="function", autouse="True")
def setup():
    from assistant.rewards import rewards_assistant

    return rewards_assistant


# @pytest.mark.skip()
def test_rewards_flow(setup):
    rewards_assistant = setup
    BadgerTreeV2 = rewards_assistant.BadgerTreeV2
    guardian = rewards_assistant.guardian
    rootUpdater = rewards_assistant.rootUpdater

    admin, proposer, validator, user = accounts[:4]

    rewardsContract = admin.deploy(BadgerTreeV2)
    rewardsContract.initialize(admin, proposer, validator)

    console.print(
        "[yellow]You may need to manually set the cycle in the contract for this test to work. See the comment titled 'SETTING CORRECT CYCLE'[/yellow]"
    )
    """
    SETTING CORRECT CYCLE
    =========================
    1. Add the following function to the BadgerTreeV2 contract:

    /// @dev test function to get cycle to starting point
    function setCycle(uint256 n) public {
        _onlyAdmin();
        currentCycle = n;
    }

    2. Uncomment the next line to set the cycle in the test contract:
    """
    # rewardsContract.setCycle(1296, {'from': admin})

    contentHash1 = "0xe8e31919bd92024a0437852392695f5424932b2d1b041ab45c319de7ce42fda0"
    contentHash2 = "0xe84f535a2581589e2c0b62040926d6599d14c436da24ab8fac5e2c86467721aa"

    with open("rewards/test-rewards-{}.json".format(contentHash1)) as f:
        rewards1 = json.load(f)

    with open("rewards/test-rewards-{}.json".format(contentHash2)) as f:
        rewards2 = json.load(f)

    console.print("Here are the merkle roots to use")
    console.print({"root1": rewards1["merkleRoot"], "root2": rewards2["merkleRoot"]})

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

    distribute_from_whales(rewardsContract, user)
    with open("build/contracts/ERC20.json") as f:
        ERC20_abi = json.load(f)["abi"]

    # first rewards cycle
    rewards_accounts = list(rewards1["claims"].keys())
    start_block = rewardsContract.lastPublishStartBlock() + 1

    with brownie.reverts("Incorrect cycle"):
        rewardsContract.proposeRoot(
            rewards1["merkleRoot"],
            contentHash1,
            hex(rewardsContract.currentCycle()),
            start_block,
            start_block + 1,
            {"from": proposer},
        )
    with brownie.reverts("Incorrect cycle"):
        rewardsContract.proposeRoot(
            rewards1["merkleRoot"],
            contentHash1,
            hex(rewardsContract.currentCycle() + 2),
            start_block,
            start_block + 1,
            {"from": proposer},
        )
    with brownie.reverts("Incorrect start block"):
        rewardsContract.proposeRoot(
            rewards1["merkleRoot"],
            contentHash1,
            hex(rewardsContract.currentCycle() + 1),
            start_block - 1,
            start_block + 1,
            {"from": proposer},
        )
    with brownie.reverts("Incorrect start block"):
        rewardsContract.proposeRoot(
            rewards1["merkleRoot"],
            contentHash1,
            hex(rewardsContract.currentCycle() + 1),
            start_block + 1,
            start_block + 1,
            {"from": proposer},
        )

    rewardsContract.proposeRoot(
        rewards1["merkleRoot"],
        contentHash1,
        hex(rewardsContract.currentCycle() + 1),
        start_block,
        start_block + 1,
        {"from": proposer},
    )
    rewardsContract.approveRoot(
        rewards1["merkleRoot"],
        contentHash1,
        rewardsContract.currentCycle() + 1,
        start_block,
        start_block + 1,
        {"from": validator},
    )

    # Test partial claims
    first_claimer = rewards_accounts[0]
    token_contract = Contract.from_abi(
        "Token1", rewards1["claims"][first_claimer]["tokens"][0], ERC20_abi
    )
    prev_balance = token_contract.balanceOf(first_claimer)
    claim_amount = int(rewards1["claims"][first_claimer]["cumulativeAmounts"][0]) // 2

    # Some claims that should fail
    with brownie.reverts("Excessive claim"):
        rewardsContract.claim(
            rewards1["claims"][first_claimer]["tokens"],
            rewards1["claims"][first_claimer]["cumulativeAmounts"],
            rewards1["claims"][first_claimer]["index"],
            rewards1["claims"][first_claimer]["cycle"],
            rewards1["claims"][first_claimer]["proof"],
            [
                int(rewards1["claims"][first_claimer]["cumulativeAmounts"][0]) + 1,
                claim_amount,
            ],
            {"from": first_claimer},
        )
    with brownie.reverts("Invalid cycle"):
        rewardsContract.claim(
            rewards1["claims"][first_claimer]["tokens"],
            rewards1["claims"][first_claimer]["cumulativeAmounts"],
            rewards1["claims"][first_claimer]["index"],
            "0x9999",
            rewards1["claims"][first_claimer]["proof"],
            [claim_amount, claim_amount],
            {"from": first_claimer},
        )
    with brownie.reverts("Invalid proof"):
        rewardsContract.claim(
            rewards1["claims"][first_claimer]["tokens"],
            rewards1["claims"][first_claimer]["cumulativeAmounts"],
            rewards1["claims"][rewards_accounts[1]]["index"],
            rewards1["claims"][first_claimer]["cycle"],
            rewards1["claims"][first_claimer]["proof"],
            [claim_amount, claim_amount],
            {"from": first_claimer},
        )
    with brownie.reverts("Invalid proof"):
        rewardsContract.claim(
            rewards1["claims"][first_claimer]["tokens"],
            rewards1["claims"][first_claimer]["cumulativeAmounts"],
            rewards1["claims"][first_claimer]["index"],
            rewards1["claims"][first_claimer]["cycle"],
            rewards1["claims"][rewards_accounts[1]]["proof"],
            [claim_amount, claim_amount],
            {"from": first_claimer},
        )
    with brownie.reverts("Invalid proof"):
        rewardsContract.claim(
            rewards1["claims"][rewards_accounts[7]]["tokens"],
            rewards1["claims"][first_claimer]["cumulativeAmounts"],
            rewards1["claims"][first_claimer]["index"],
            rewards1["claims"][first_claimer]["cycle"],
            rewards1["claims"][first_claimer]["proof"],
            [claim_amount, claim_amount],
            {"from": first_claimer},
        )
    with brownie.reverts("Invalid proof"):
        rewardsContract.claim(
            rewards1["claims"][first_claimer]["tokens"],
            rewards1["claims"][rewards_accounts[7]]["cumulativeAmounts"],
            rewards1["claims"][first_claimer]["index"],
            rewards1["claims"][first_claimer]["cycle"],
            rewards1["claims"][first_claimer]["proof"],
            [claim_amount, claim_amount],
            {"from": first_claimer},
        )
    with brownie.reverts("No tokens to claim"):
        rewardsContract.claim(
            rewards1["claims"][first_claimer]["tokens"],
            rewards1["claims"][first_claimer]["cumulativeAmounts"],
            rewards1["claims"][first_claimer]["index"],
            rewards1["claims"][first_claimer]["cycle"],
            rewards1["claims"][first_claimer]["proof"],
            [0, 0],
            {"from": first_claimer},
        )
    with brownie.reverts("Excessive claim"):
        rewardsContract.claim(
            rewards1["claims"][first_claimer]["tokens"],
            rewards1["claims"][first_claimer]["cumulativeAmounts"],
            rewards1["claims"][first_claimer]["index"],
            rewards1["claims"][first_claimer]["cycle"],
            rewards1["claims"][first_claimer]["proof"],
            [int(rewards1["claims"][first_claimer]["cumulativeAmounts"][0]) + 1, 0],
            {"from": first_claimer},
        )

    # Make two successful partial claims
    rewardsContract.claim(
        rewards1["claims"][first_claimer]["tokens"],
        rewards1["claims"][first_claimer]["cumulativeAmounts"],
        rewards1["claims"][first_claimer]["index"],
        rewards1["claims"][first_claimer]["cycle"],
        rewards1["claims"][first_claimer]["proof"],
        [claim_amount, 0],
        {"from": first_claimer},
    )
    assert prev_balance + claim_amount == token_contract.balanceOf(first_claimer)

    rewardsContract.claim(
        rewards1["claims"][first_claimer]["tokens"],
        rewards1["claims"][first_claimer]["cumulativeAmounts"],
        rewards1["claims"][first_claimer]["index"],
        rewards1["claims"][first_claimer]["cycle"],
        rewards1["claims"][first_claimer]["proof"],
        [claim_amount, 0],
        {"from": first_claimer},
    )
    assert prev_balance + claim_amount + claim_amount == token_contract.balanceOf(
        first_claimer
    )

    # Second rewards cycle
    chain.mine(10)
    start_block = rewardsContract.lastPublishStartBlock() + 1

    rewardsContract.proposeRoot(
        rewards2["merkleRoot"],
        contentHash2,
        hex(rewardsContract.currentCycle() + 1),
        start_block,
        start_block + 1,
        {"from": proposer},
    )
    rewardsContract.approveRoot(
        rewards2["merkleRoot"],
        contentHash2,
        rewardsContract.currentCycle() + 1,
        start_block,
        start_block + 1,
        {"from": validator},
    )

    # Claim from previous cycle
    second_claimer = rewards_accounts[1]
    token_contract1 = Contract.from_abi(
        "Token1", rewards1["claims"][second_claimer]["tokens"][0], ERC20_abi
    )
    token_contract2 = Contract.from_explorer(
        rewards1["claims"][second_claimer]["tokens"][1]
    )  # Digg token contract
    prev_balance1 = token_contract1.balanceOf(second_claimer)
    prev_balance2 = token_contract2.balanceOf(second_claimer)
    claim_amount1 = int(rewards1["claims"][second_claimer]["cumulativeAmounts"][0])
    claim_amount2 = int(rewards1["claims"][second_claimer]["cumulativeAmounts"][1])

    rewardsContract.claim(
        rewards1["claims"][second_claimer]["tokens"],
        rewards1["claims"][second_claimer]["cumulativeAmounts"],
        rewards1["claims"][second_claimer]["index"],
        rewards1["claims"][second_claimer]["cycle"],
        rewards1["claims"][second_claimer]["proof"],
        [claim_amount1, claim_amount2],
        {"from": second_claimer},
    )
    assert prev_balance1 + claim_amount1 == token_contract1.balanceOf(second_claimer)
    # Calculation for Digg balance:
    assert Decimal(prev_balance2 + claim_amount2) // Decimal(
        token_contract2._sharesPerFragment()
    ) == token_contract2.balanceOf(second_claimer)

    # Claim from current cycle
    prev_balance1 = token_contract1.balanceOf(second_claimer)
    prev_balance2 = token_contract2.balanceOf(second_claimer)
    claim_amount1 = int(rewards2["claims"][second_claimer]["cumulativeAmounts"][0])
    claim_amount2 = int(rewards2["claims"][second_claimer]["cumulativeAmounts"][1])

    # can't claim full cumulative amount for this current cycle since majority was claimed last cycle
    with brownie.reverts("Excessive claim"):
        rewardsContract.claim(
            rewards2["claims"][second_claimer]["tokens"],
            rewards2["claims"][second_claimer]["cumulativeAmounts"],
            rewards2["claims"][second_claimer]["index"],
            rewards2["claims"][second_claimer]["cycle"],
            rewards2["claims"][second_claimer]["proof"],
            [claim_amount1, claim_amount2],
            {"from": second_claimer},
        )

    # claim remaining rewards for new cycle
    prev_claimable = rewardsContract.getClaimableFor(
        second_claimer,
        rewards2["claims"][second_claimer]["tokens"],
        rewards2["claims"][second_claimer]["cumulativeAmounts"],
    )

    rewardsContract.claim(
        rewards2["claims"][second_claimer]["tokens"],
        rewards2["claims"][second_claimer]["cumulativeAmounts"],
        rewards2["claims"][second_claimer]["index"],
        rewards2["claims"][second_claimer]["cycle"],
        rewards2["claims"][second_claimer]["proof"],
        [prev_claimable[1][0], prev_claimable[1][1]],
        {"from": second_claimer},
    )

    claimable = rewardsContract.getClaimableFor(
        second_claimer,
        rewards2["claims"][second_claimer]["tokens"],
        rewards2["claims"][second_claimer]["cumulativeAmounts"],
    )
    assert claimable[1][0] == 0
    assert claimable[1][1] == 0
