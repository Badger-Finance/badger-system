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


def get_cumulative_claimable_for_token(claim, token):
    console.print("Find claim for", token)
    tokens = claim["tokens"]
    amounts = claim["cumulativeAmounts"]

    console.log(tokens, amounts)

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


def publish_new_root(badger, root, contentHash):
    """
    Publish new root from local file
    """

    tree = badger.badgerTree

    rootProposer = accounts.at(tree.getRoleMember(ROOT_PROPOSER_ROLE, 0), force=True)
    rootValidator = accounts.at(tree.getRoleMember(ROOT_VALIDATOR_ROLE, 0), force=True)

    lastProposeEndBlock = tree.lastProposeEndBlock()
    currentCycle = tree.currentCycle()

    endBlock = chain.height

    tree.proposeRoot(
        root,
        contentHash,
        currentCycle + 1,
        lastProposeEndBlock + 1,
        endBlock,
        {"from": rootProposer},
    )

    chain.mine()

    tree.approveRoot(
        root,
        contentHash,
        currentCycle + 1,
        lastProposeEndBlock + 1,
        endBlock,
        {"from": rootValidator},
    )
