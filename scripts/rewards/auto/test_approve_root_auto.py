import json
import time

from assistant.rewards.aws_utils import upload
from assistant.rewards.rewards_assistant import (
    content_hash_to_filename,
    fetch_current_rewards_tree,
    fetchCurrentMerkleData,
    fetchPendingMerkleData,
    run_action,
)
from assistant.rewards.rewards_checker import verify_rewards
from brownie import *
from config.badger_config import badger_config
from helpers.gas_utils import gas_strategies
from rich.console import Console
from scripts.rewards.rewards_utils import (
    get_last_proposed_cycle,
    get_last_published_cycle,
)
from scripts.systems.badger_system import BadgerSystem, LoadMethod, connect_badger

console = Console()

gas_strategies.set_default(gas_strategies.exponentialScaling)


def hash(value):
    return web3.toHex(web3.keccak(text=value))


def approve_root(badger: BadgerSystem):
    badgerTree = badger.badgerTree
    if not badgerTree.hasPendingRoot():
        console.print("No pending root")
        return False

    if rpc.is_active():
        badger.guardian = accounts.at(
            "0x626F69162Ea1556A75Dd4443D87D2fe38dd25901", force=True
        )

    current = fetchCurrentMerkleData(badger)
    pending = fetchPendingMerkleData(badger)

    (publishedRewards, sb, eb) = get_last_published_cycle(badger)
    (proposedRewards, startBlock, endBlock) = get_last_proposed_cycle(badger)

    console.print(proposedRewards["merkleRoot"])

    rootHash = hash(proposedRewards["merkleRoot"])
    contentFileName = content_hash_to_filename(rootHash)
    print("Uploading to file " + contentFileName)

    with open(contentFileName, "w") as outfile:
        json.dump(proposedRewards, outfile, indent=4)

    with open(contentFileName) as f:
        after_file = json.load(f)

    console.print(contentFileName)

    print(
        proposedRewards["merkleRoot"],
        startBlock,
        endBlock,
        badgerTree.lastProposeStartBlock(),
        badgerTree.lastProposeEndBlock(),
    )

    verify_rewards(badger, startBlock, endBlock, publishedRewards, proposedRewards)

    badgerTree.approveRoot(
        proposedRewards["merkleRoot"],
        pending["contentHash"],
        proposedRewards["cycle"],
        startBlock,
        endBlock,
        {"from": badger.guardian, "gas_limit": 3000000, "allow_revert": True},
    )

    upload(contentFileName)

    # (currentRewards, startBlock, endBlock) = get_last_proposed_cycle(badger)
    # rootApproved = run_action(
    #     badger,
    #     {
    #         "action": "guardian",
    #         "startBlock": startBlock,
    #         "endBlock": endBlock,
    #         "pastRewards": currentRewards,
    #     },
    #     test=False,
    # )


def main():
    badger = connect_badger(load_guardian=True, load_method=LoadMethod.SK)

    # If there is a pending root, approve after independently verifying it
    while True:
        try:
            approve_root(badger)
        except Exception as e:
            console.print("[red]Error[/red]", e)
        finally:
            time.sleep(10 * 60)
