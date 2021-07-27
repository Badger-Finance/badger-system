from assistant.subgraph.client import fetch_wallet_balances
import json
from brownie import *
from brownie.network.gas.strategies import GasNowStrategy
from config.rewards_config import rewards_config
from helpers.time_utils import to_hours
from rich.console import Console
from assistant.rewards.aws_utils import (
    download_latest_tree,
    download_tree,
    upload,
    upload_boosts,
)
from typing import Dict

from assistant.rewards.snapshot.utils import chain_snapshot
from assistant.rewards.meta_rewards.sushi import calc_all_sushi_rewards
from assistant.rewards.meta_rewards.tree_rewards import calc_tree_rewards
from assistant.rewards.meta_rewards.unclaimed_rewards import get_unclaimed_rewards
from assistant.rewards.calc_rewards import calc_rewards
from assistant.rewards.rewards_utils import (
    keccak,
    process_cumulative_rewards,
    combine_rewards,
)
from assistant.rewards.classes.MerkleTree import rewards_to_merkle_tree
from assistant.rewards.classes.RewardsLog import rewardsLog

from assistant.rewards.rewards_checker import compare_rewards, verify_rewards
from scripts.systems.badger_system import BadgerSystem
from helpers.gas_utils import gas_strategies
from helpers.constants import BCVX, BCVXCRV

gas_strategies.set_default(gas_strategies.exponentialScalingFast)
gas_strategy = gas_strategies.exponentialScalingFast
console = Console()


def calc_sett_rewards(
    badger: BadgerSystem,
    startBlock: int,
    endBlock: int,
    cycle: int,
    chain: str,
    unclaimedRewards: Dict[str, Dict[str, int]],
    boost,
):

    """
    Calculate rewards for each sett on a chain and sum them
    :param badger: badger system
    :param startBlock: start of cycle
    :param endBlock: end of cycle
    :param cycle: number of current cycle
    :param chain: chain to calculate rewards for
    :param unclaimedRewards: all unclaimed rewards for users on current chain
    :param boost: badger boost multipliers
    """
    balancesBySett = chain_snapshot(badger, chain, endBlock)
    rewards = []
    for sett, balances in balancesBySett.items():
        settRewards = calc_rewards(
            badger, sett, balances, startBlock, endBlock, chain, boost
        )
        rewards.append(settRewards)

    return combine_rewards(rewards, cycle, badger.badgerTree)


def fetchPendingMerkleData(badger: BadgerSystem):
    # currentMerkleData = badger.badgerTree.getPendingMerkleData()
    # root = str(currentMerkleData[0])
    # contentHash = str(currentMerkleData[1])
    # lastUpdateTime = currentMerkleData[2]
    # blockNumber = currentMerkleData[3]

    root = badger.badgerTree.pendingMerkleRoot()
    contentHash = badger.badgerTree.pendingMerkleContentHash()
    lastUpdateTime = badger.badgerTree.lastProposeTimestamp()
    blockNumber = badger.badgerTree.lastProposeBlockNumber()

    return {
        "root": root,
        "contentHash": contentHash,
        "lastUpdateTime": lastUpdateTime,
        "blockNumber": int(blockNumber),
    }


def fetchCurrentMerkleData(badger: BadgerSystem):
    # currentMerkleData = badger.badgerTree.getCurrentMerkleData()
    # root = str(currentMerkleData[0])
    # contentHash = str(currentMerkleData[1])
    # lastUpdateTime = currentMerkleData[2]
    # blockNumber = badger.badgerTree.lastPublishBloc)

    root = badger.badgerTree.merkleRoot()
    contentHash = badger.badgerTree.merkleContentHash()
    lastUpdateTime = badger.badgerTree.lastPublishTimestamp()
    blockNumber = badger.badgerTree.lastPublishBlockNumber()

    return {
        "root": root,
        "contentHash": contentHash,
        "lastUpdateTime": lastUpdateTime,
        "blockNumber": int(blockNumber),
    }


def getNextCycle(badger: BadgerSystem):
    return badger.badgerTree.currentCycle() + 1


def fetch_pending_rewards_tree(badger, print_output=False):
    # TODO Files should be hashed and signed by keeper to prevent tampering
    # TODO How will we upload addresses securely?
    # We will check signature before posting
    merkle = fetchPendingMerkleData(badger)
    pastFile = "rewards-1-" + str(merkle["contentHash"]) + ".json"

    if print_output:
        console.print(
            "[green]===== Loading Pending Rewards " + pastFile + " =====[/green]"
        )

    currentTree = json.loads(download_tree(pastFile))

    # Invariant: File shoulld have same root as latest
    assert currentTree["merkleRoot"] == merkle["root"]

    lastUpdatePublish = merkle["blockNumber"]
    lastUpdate = int(currentTree["endBlock"])

    if print_output:
        print(
            "lastUpdateBlock", lastUpdate, "lastUpdatePublishBlock", lastUpdatePublish
        )
    # Ensure upload was after file tracked
    assert lastUpdatePublish >= lastUpdate

    # Ensure file tracks block within 1 day of upload
    assert abs(lastUpdate - lastUpdatePublish) < 6500

    return currentTree


def fetch_current_rewards_tree(badger, print_output=False):
    # TODO Files should be hashed and signed by keeper to prevent tampering
    # TODO How will we upload addresses securely?
    # We will check signature before posting
    merkle = fetchCurrentMerkleData(badger)
    pastFile = "rewards-1-" + str(merkle["contentHash"]) + ".json"

    console.print(
        "[bold yellow]===== Loading Past Rewards " + pastFile + " =====[/bold yellow]"
    )

    currentTree = json.loads(download_tree(pastFile))

    # Invariant: File shoulld have same root as latest
    console.print(merkle)
    console.print("liveRoot", merkle["root"])
    console.print("fileRoot", currentTree["merkleRoot"])

    assert currentTree["merkleRoot"] == merkle["root"]

    lastUpdateOnChain = merkle["blockNumber"]
    lastUpdate = int(currentTree["endBlock"])

    print("lastUpdateOnChain ", lastUpdateOnChain, " lastUpdate ", lastUpdate)
    # Ensure file tracks block within 1 day of upload
    assert abs(lastUpdate - lastUpdateOnChain) < 6500

    # Ensure upload was after file tracked
    assert lastUpdateOnChain >= lastUpdate
    return currentTree


def generate_rewards_in_range(badger, startBlock, endBlock, pastRewards, saveLocalFile):
    endBlock = endBlock
    blockDuration = endBlock - startBlock

    nextCycle = getNextCycle(badger)

    currentMerkleData = fetchCurrentMerkleData(badger)
    # farmRewards = fetch_current_harvest_rewards(badger,startBlock, endBlock,nextCycle)
    unclaimedAddresses = []
    for addr, data in pastRewards["claims"].items():
        tokens = data["tokens"]
        if BCVX in tokens or BCVXCRV in tokens:
            unclaimedAddresses.append(addr)

    sushiRewards = calc_all_sushi_rewards(badger, startBlock, endBlock, nextCycle)
    treeRewards = calc_tree_rewards(badger, startBlock, endBlock, nextCycle)
    settRewards = calc_sett_rewards(
        badger,
        startBlock,
        endBlock,
        nextCycle,
        get_unclaimed_rewards(unclaimedAddresses),
    )

    newRewards = combine_rewards(
        [settRewards, treeRewards, sushiRewards], nextCycle, badger.badgerTree
    )
    cumulativeRewards = process_cumulative_rewards(pastRewards, newRewards)

    # Take metadata from geyserRewards
    console.print("Processing to merkle tree")
    merkleTree = rewards_to_merkle_tree(cumulativeRewards, startBlock, endBlock, {})

    # Publish data
    rootHash = keccak(merkleTree["merkleRoot"])

    contentFileName = content_hash_to_filename(rootHash)

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
    rewardsLog.set_merkle_root(merkleTree["merkleRoot"])
    rewardsLog.set_content_hash(str(rootHash))
    rewardsLog.set_start_block(startBlock)
    rewardsLog.set_end_block(endBlock)
    print("Uploading to file " + contentFileName)

    rewardsLog.save(nextCycle)
    # TODO: Upload file to AWS & serve from server
    if saveLocalFile:
        with open(contentFileName, "w") as outfile:
            json.dump(merkleTree, outfile, indent=4)

    # Sanity check new rewards file

    verify_rewards(badger, startBlock, endBlock, pastRewards, merkleTree)

    return {
        "contentFileName": contentFileName,
        "merkleTree": merkleTree,
        "rootHash": rootHash,
    }


def rootUpdater(badger, startBlock, endBlock, pastRewards, saveLocalFile, test=False):
    """
    Root Updater Role
    - Check how much time has passed since the last published update
    - If sufficient time has passed, run the rewards script and p
    - If there is a discrepency, notify admin

    (In case of a one-off failure, Script will be attempted again at the rootUpdaterInterval)
    """
    console.print("\n[bold cyan]===== Root Updater =====[/bold cyan]\n")

    badgerTree = badger.badgerTree
    nextCycle = getNextCycle(badger)

    currentMerkleData = fetchCurrentMerkleData(badger)
    currentTime = chain.time()

    console.print(
        "\n[green]Calculate rewards for {} blocks: {} -> {} [/green]\n".format(
            endBlock - startBlock, startBlock, endBlock
        )
    )

    # Only run if we have sufficent time since previous root
    timeSinceLastupdate = currentTime - currentMerkleData["lastUpdateTime"]
    if timeSinceLastupdate < rewards_config.rootUpdateMinInterval and not test:
        console.print(
            "[bold yellow]===== Result: Last Update too Recent ({}) =====[/bold yellow]".format(
                to_hours(timeSinceLastupdate)
            )
        )
        return False

    rewards_data = generate_rewards_in_range(
        badger, startBlock, endBlock, pastRewards, saveLocalFile
    )

    console.print("===== Root Updater Complete =====")
    if not test:

        badgerTree.proposeRoot(
            rewards_data["merkleTree"]["merkleRoot"],
            rewards_data["rootHash"],
            rewards_data["merkleTree"]["cycle"],
            rewards_data["merkleTree"]["startBlock"],
            rewards_data["merkleTree"]["endBlock"],
            {"from": badger.root_proposer, "gas_price": gas_strategy},
        )
        upload(
            rewards_data["contentFileName"], rewards_data["merkleTree"], publish=False
        )

    return rewards_data


def guardian(
    badger: BadgerSystem, startBlock, endBlock, pastRewards, saveLocalFile, test=False
):
    """
    Guardian Role
    - Check if there is a new proposed root
    - If there is, run the rewards script at the same block height to verify the results
    - If there is a discrepency, notify admin
    (In case of a one-off failure, Script will be attempted again at the guardianInterval)
    """

    console.print("\n[bold cyan]===== Guardian =====[/bold cyan]\n")

    console.print(
        "\n[green]Calculate rewards for {} blocks: {} -> {} [/green]\n".format(
            endBlock - startBlock, startBlock, endBlock
        )
    )

    badgerTree = badger.badgerTree

    # Only run if we have a pending root
    if not badgerTree.hasPendingRoot():
        console.print("[bold yellow]===== Result: No Pending Root =====[/bold yellow]")
        return False

    rewards_data = generate_rewards_in_range(
        badger, startBlock, endBlock, pastRewards, saveLocalFile
    )

    console.print("===== Guardian Complete =====")

    if not test:
        badgerTree.approveRoot(
            rewards_data["merkleTree"]["merkleRoot"],
            rewards_data["rootHash"],
            rewards_data["merkleTree"]["cycle"],
            rewards_data["merkleTree"]["startBlock"],
            rewards_data["merkleTree"]["endBlock"],
            {"from": badger.guardian, "gas_price": gas_strategy},
        )
        upload(rewards_data["contentFileName"], rewards_data["merkleTree"]),


def run_action(badger, args, test, saveLocalFile=True):
    if args["action"] == "rootUpdater":
        return rootUpdater(
            badger,
            args["startBlock"],
            args["endBlock"],
            args["pastRewards"],
            saveLocalFile,
            test,
        )
    if args["action"] == "guardian":
        return guardian(
            badger,
            args["startBlock"],
            args["endBlock"],
            args["pastRewards"],
            saveLocalFile,
            test,
        )
    return False


def content_hash_to_filename(contentHash: str):
    return "rewards-" + str(chain.id) + "-" + str(contentHash) + ".json"
