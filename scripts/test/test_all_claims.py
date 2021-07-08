from assistant.rewards.rewards_assistant import fetch_current_rewards_tree
import json
import secrets
import random
from tabulate import tabulate
import brownie
import pytest
from brownie import *
from helpers.constants import *
from helpers.registry import registry
from helpers.gnosis_safe import GnosisSafe, MultisigTxMetadata
from rich.console import Console
from config.badger_config import badger_config
from scripts.systems.badger_system import connect_badger
from helpers.utils import val
from helpers.token_utils import token_metadata, get_token_balances

console = Console()
debug = False


def get_cumulative_claimable_for_token(claim, token):
    tokens = claim["tokens"]
    amounts = claim["cumulativeAmounts"]

    for i in range(len(tokens)):
        address = tokens[i]
        if token == address:
            return int(amounts[i])

    # If address was not found
    return 0


def get_claimed_for_token(data, token):
    tokens = data[0]
    amounts = data[1]

    for i in range(len(tokens)):
        address = tokens[i]
        if token == address:
            return amounts[i]


def test_claim(badger, user, claim, tokens_to_check):
    digg = badger.digg
    tree = badger.badgerTree

    total_claimed_before = tree.getClaimedFor(user, tokens_to_check)

    print("=== Claim: " + user + " ===")

    accounts[0].transfer(user, Wei("0.5 ether"))
    userAccount = accounts.at(user, force=True)

    table = []

    assert tree.merkleRoot() == root

    pre = get_token_balances(tokens_to_check, [userAccount])

    parsed_amounts = []
    for amount in claim["cumulativeAmounts"]:
        parsed_amounts.append(int(amount))

    tokens = claim["tokens"]
    amounts = claim["cumulativeAmounts"]

    canClaim = tree.isClaimAvailableFor(user, claim["tokens"], parsed_amounts)
    claimable = tree.getClaimableFor(user, claim["tokens"], claim["cumulativeAmounts"])[
        1
    ]
    print(claimable)
    # console.log("canClaim Test", user, tokens, amounts, parsed_amounts)
    console.log("canClaim Test", canClaim)

    # Get claimable amounts before to test against reality

    if canClaim:
        tx = tree.claim(
            claim["tokens"],
            claim["cumulativeAmounts"],
            claim["index"],
            claim["cycle"],
            claim["proof"],
            claimable,
            {"from": userAccount},
        )
        # with brownie.reverts("excessive claim"):
        try:
            console.print("[red]===== 🐻 Trying to claim twice=====[/red]")
            tree.claim(
                claim["tokens"],
                claim["cumulativeAmounts"],
                claim["index"],
                claim["cycle"],
                claim["proof"],
                claimable,
                {"from": user, "allow_revert": True},
            )
        except Exception as e:
            console.print("Double Claim Attempt", e)

    # Ensure fail if no claim
    else:
        console.print("[yellow]===== 🍄 Trying to claim when no claim=====[/yellow]")
        try:
            tree.claim(
                claim["tokens"],
                claim["cumulativeAmounts"],
                claim["index"],
                claim["cycle"],
                claim["proof"],
                claimable,
                {"from": user, "allow_revert": True},
            )
        except Exception as e:
            console.print("No tokens claim", e)

    # Test double claim on same data set

    post = get_token_balances(tokens_to_check, [userAccount])
    claimed_totals_after = tree.getClaimedFor(user, tokens_to_check)

    for token in post.balances.keys():
        cumulative_claimed = int(claim["cumulativeAmounts"][0])
        cumulative_claimed = get_cumulative_claimable_for_token(claim, token)
        claimed_for_token_before = get_claimed_for_token(total_claimed_before, token)
        claimed_for_token_after = get_claimed_for_token(claimed_totals_after, token)

        if debug:
            console.print(
                {
                    "token": token,
                    "cumulative_claimed": cumulative_claimed,
                    "claimed_for_token_after": claimed_for_token_after,
                    "claimed_for_token_before": claimed_for_token_before,
                }
            )

        expected_claim = cumulative_claimed - claimed_for_token_before
        pre_amount = pre.get(token, user)
        post_amount = post.get(token, user)
        diff = post_amount - pre_amount
        table.append(
            [
                user,
                token_metadata.get_symbol(token),
                # val(pre_amount, decimals=token_metadata.get_decimals(token)),
                # val(post_amount, decimals=token_metadata.get_decimals(token)),
                val(diff, decimals=token_metadata.get_decimals(token)),
                val(expected_claim, token_metadata.get_decimals(token)),
                val(cumulative_claimed, token_metadata.get_decimals(token)),
            ]
        )

    print(
        tabulate(
            table,
            headers=[
                "user",
                "token",
                # "before",
                # "after",
                "diff",
                "claim",
                "culumativeClaimed",
            ],
        )
    )

    assert cumulative_claimed == claimed_for_token_after
    assert post_amount == pre_amount + expected_claim


# @pytest.mark.skip()
def test_rewards_flow():
    badger = connect_badger(badger_config.prod_json)
    tree = badger.badgerTree
    pct_claims_to_verify = 0.001

    tokens_to_check = [
        badger.token,
        badger.digg.token,
        interface.IERC20(registry.sushi.xsushiToken),
        interface.IERC20(registry.harvest.farmToken),
    ]

    # newLogic = BadgerTree.deploy({"from": badger.deployer})
    newLogic = BadgerTree.at("0x0f81D3f48Fedb8E67a5b87A8a4De57766157f19B")

    multi = GnosisSafe(badger.opsMultisig)

    # Test claimable amounts

    # ===== Test VS Existing List =====
    # active_claims = fetch_current_rewards_tree(badger)
    # claims = active_claims["claims"]

    # users_to_verify = []

    # # Test claims with latest root
    # for user, claim in claims.items():
    #     roll = random.random()
    #     if roll < pct_claims_to_verify:
    #         console.print(roll, pct_claims_to_verify)
    #         users_to_verify.append(user)
    #         test_claim(badger, user, claim, tokens_to_check)

    retroactive_content_hash = (
        "0x346ec98585b52d981d43584477e1b831ce32165cb8e0a06d14d236241b36328e"
    )
    retroactive_file_name = "rewards-1-" + retroactive_content_hash + ".json"

    with open(retroactive_file_name) as f:
        rewards = json.load(f)

    # Update to new root with xSushi and FARM
    rootProposer = accounts.at(tree.getRoleMember(ROOT_PROPOSER_ROLE, 0), force=True)
    rootValidator = accounts.at(tree.getRoleMember(ROOT_VALIDATOR_ROLE, 0), force=True)

    lastProposeEndBlock = tree.lastProposeEndBlock()
    currentCycle = tree.currentCycle()

    endBlock = chain.height

    root = rewards["merkleRoot"]
    # root = tree.merkleRoot()

    tree.proposeRoot(
        root,
        retroactive_content_hash,
        currentCycle + 1,
        lastProposeEndBlock + 1,
        endBlock,
        {"from": rootProposer},
    )

    tree.approveRoot(
        root,
        retroactive_content_hash,
        currentCycle + 1,
        lastProposeEndBlock + 1,
        endBlock,
        {"from": rootValidator},
    )

    assert tree.merkleRoot() == root
    assert tree.currentCycle() == currentCycle + 1

    console.print("[blue]===== After Retroactive Root =====[/blue]")
    console.print(rewards["merkleRoot"], rewards["cycle"])
    retroactive_claims = rewards["claims"]

    users_to_verify = []

    # Test claims with latest root
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


def publish_new_root(badger, root, contentHash):
    """
    Publish new root from local file
    """

    tree = badger.badgerTree

    local_file_path = "rewards-1-" + contentHash + "json"
    with open(local_file_path) as f:
        rewards = json.load(f)


def main():
    test_rewards_flow()
