from brownie import *
from helpers.constants import *
from rich.console import Console

console = Console()


def get_cumulative_claimable_for_token(claim, token):
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
