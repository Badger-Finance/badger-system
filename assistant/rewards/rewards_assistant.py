import json
from brownie import *
from brownie.network.gas.strategies import GasNowStrategy
from config.rewards_config import rewards_config
from helpers.time_utils import to_hours
from rich.console import Console
from tqdm import tqdm
from assistant.rewards.boost import badger_boost
from assistant.rewards.twap import digg_btc_twap, calculate_digg_allocation
from assistant.rewards.aws_utils import (
    download_latest_tree,
    download_tree,
    upload,
    upload_boosts,
)
from assistant.rewards.calc_snapshot import calc_snapshot
from assistant.rewards.meta_rewards.harvest import calc_farm_rewards
from assistant.rewards.meta_rewards.sushi import calc_all_sushi_rewards
from assistant.rewards.rewards_utils import (
    sum_rewards,
    keccak,
    process_cumulative_rewards,
    combine_rewards,
)
from assistant.rewards.classes.MerkleTree import rewards_to_merkle_tree
from assistant.rewards.classes.RewardsList import RewardsList
from assistant.rewards.classes.RewardsLog import rewardsLog

from assistant.rewards.rewards_checker import compare_rewards, verify_rewards
from scripts.systems.badger_system import BadgerSystem
from helpers.gas_utils import gas_strategies

gas_strategies.set_default(gas_strategies.exponentialScalingFast)
gas_strategy = gas_strategies.exponentialScalingFast
console = Console()


def calc_sett_rewards(badger, periodStartBlock, endBlock, cycle):
    """
    Calculate rewards for each sett, and sum them
    """
    # ratio = digg_btc_twap(periodStartBlock,endBlock)
    # diggAllocation = calculate_digg_allocation(ratio)
    rewardsBySett = {}
    noRewards = ["native.digg", "experimental.digg"]
    boosts = badger_boost(badger, endBlock)
    apyBoosts = {}
    multiplierData = {}
    for key, sett in badger.sett_system.vaults.items():
        if key in noRewards:
            continue

        settRewards, apyBoost = calc_snapshot(
            badger, key, periodStartBlock, endBlock, cycle, boosts, 0
        )
        if len(apyBoost) > 0:
            minimum = min(apyBoost.values())
            maximum = max(apyBoost.values())
            multiplierData[sett.address] = {"min": minimum, "max": maximum}
            for addr in apyBoost:
                if addr not in apyBoosts:
                    apyBoosts[addr] = {}
                apyBoosts[addr][sett.address] = apyBoost[addr]

        rewardsBySett[key] = settRewards

    rewards = combine_rewards(list(rewardsBySett.values()), cycle, badger.badgerTree)
    boostsMetadata = {"multiplierData": multiplierData, "userData": {}}

    for addr, multipliers in apyBoosts.items():
        boostsMetadata["userData"][addr] = {
            "boost": boosts.get(addr, 1),
            "multipliers": multipliers,
        }

    with open("badger-boosts.json", "w") as fp:
        json.dump(boostsMetadata, fp)

    upload_boosts(test=True)

    return rewards


def fetchPendingMerkleData(badger):
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


def fetchCurrentMerkleData(badger):
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


def getNextCycle(badger):
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


def generate_rewards_in_range(badger, startBlock, endBlock, pastRewards):
    endBlock = endBlock
    blockDuration = endBlock - startBlock

    nextCycle = getNextCycle(badger)

    currentMerkleData = fetchCurrentMerkleData(badger)
    # sushiRewards = calc_sushi_rewards(badger,startBlock,endBlock,nextCycle,retroactive=False)
    # farmRewards = fetch_current_harvest_rewards(badger,startBlock, endBlock,nextCycle)
    settRewards = calc_sett_rewards(badger, startBlock, endBlock, nextCycle)

    # farmRewards = calc_farm_rewards(
    #    badger, startBlock, endBlock, nextCycle, retroactive=False
    # )
    # sushiRewards = calc_all_sushi_rewards(
    #    badger, startBlock, endBlock, nextCycle, retroactive=False
    # )

    newRewards = combine_rewards([settRewards], nextCycle, badger.badgerTree)
    cumulativeRewards = process_cumulative_rewards(pastRewards, newRewards)

    # Take metadata from geyserRewards
    console.print("Processing to merkle tree")
    merkleTree = rewards_to_merkle_tree(cumulativeRewards, startBlock, endBlock, {})

    # Publish data
    rootHash = keccak(merkleTree["merkleRoot"])
    rewardsLog.set_merkle_root(rootHash)

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
    print("Uploading to file " + contentFileName)

    rewardsLog.save("rewards-{}".format(nextCycle))
    # TODO: Upload file to AWS & serve from server
    with open(contentFileName, "w") as outfile:
        json.dump(merkleTree, outfile, indent=4)

    with open(contentFileName) as f:
        after_file = json.load(f)

    # Sanity check new rewards file

    verify_rewards(
        badger, startBlock, endBlock, pastRewards, after_file,
    )

    return {
        "contentFileName": contentFileName,
        "merkleTree": merkleTree,
        "rootHash": rootHash,
    }


def rootUpdater(badger, startBlock, endBlock, pastRewards, test=False):
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

    rewards_data = generate_rewards_in_range(badger, startBlock, endBlock, pastRewards)

    console.print("===== Root Updater Complete =====")
    if not test:

        badgerTree.proposeRoot(
            rewards_data["merkleTree"]["merkleRoot"],
            rewards_data["rootHash"],
            rewards_data["merkleTree"]["cycle"],
            rewards_data["merkleTree"]["startBlock"],
            rewards_data["merkleTree"]["endBlock"],
            {"from": badger.keeper, "gas_price": gas_strategy},
        )
        upload(rewards_data["contentFileName"], publish=False)

    return rewards_data


def guardian(badger: BadgerSystem, startBlock, endBlock, pastRewards, test=False):
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

    rewards_data = generate_rewards_in_range(badger, startBlock, endBlock, pastRewards)

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
        upload(rewards_data["contentFileName"]),
        


def run_action(badger, args, test):
    if args["action"] == "rootUpdater":
        return rootUpdater(
            badger, args["startBlock"], args["endBlock"], args["pastRewards"], test
        )
    if args["action"] == "guardian":
        return guardian(
            badger, args["startBlock"], args["endBlock"], args["pastRewards"], test
        )
    return False


def content_hash_to_filename(contentHash):
    return "rewards-" + str(chain.id) + "-" + str(contentHash) + ".json"
