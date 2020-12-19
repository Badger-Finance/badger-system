import json

from assistant.rewards.aws_utils import upload
from assistant.rewards.calc_stakes import calc_geyser_stakes
from assistant.rewards.merkle_tree import rewards_to_merkle_tree
from assistant.rewards.rewards_checker import compare_rewards
from assistant.rewards.RewardsList import RewardsList
from brownie import *
from brownie.network.gas.strategies import GasNowStrategy
from config.rewards_config import rewards_config
from eth_abi import decode_single, encode_single
from eth_abi.packed import encode_abi_packed
from helpers.time_utils import hours
from rich.console import Console
from scripts.systems.badger_system import BadgerSystem

gas_strategy = GasNowStrategy("fast")

console = Console()


def sum_rewards(sources, cycle, badgerTree):
    """
    Sum rewards from all given set of rewards' list, returning a single rewards list
    """
    totals = RewardsList(cycle, badgerTree)
    total = 0
    # For each rewards list entry
    for key, rewardsSet in sources.items():
        # Get the claims data
        claims = rewardsSet["claims"]
        metadata = rewardsSet["metadata"]

        # Add values from each user
        for user, userData in claims.items():
            totals.track_user_metadata(user, metadata)

            # For each token
            for token, tokenAmount in userData.items():
                totals.increase_user_rewards(user, token, tokenAmount)

                total += tokenAmount
    totals.badgerSum = total
    # totals.printState()
    return totals


def calc_geyser_rewards(badger, periodStartBlock, endBlock, cycle):
    """
    Calculate rewards for each geyser, and sum them
    userRewards = (userShareSeconds / totalShareSeconds) / tokensReleased
    (For each token, for the time period)
    """
    rewardsByGeyser = {}

    # For each Geyser, get a list of user to weights
    for key, geyser in badger.geysers.items():
        geyserRewards = calc_geyser_stakes(key, geyser, periodStartBlock, endBlock)
        rewardsByGeyser[key] = geyserRewards

    return sum_rewards(rewardsByGeyser, cycle, badger.badgerTree)


def calc_harvest_meta_farm_rewards(badger, startBlock, endBlock):
    # TODO: Add harvest reward
    return RewardsList()


def process_cumulative_rewards(current, new: RewardsList):
    result = RewardsList(new.cycle, new.badgerTree)

    # Add new rewards
    for user, claims in new.claims.items():
        for token, claim in claims.items():
            result.increase_user_rewards(user, token, claim)

    # Add existing rewards
    for user, userData in current["claims"].items():
        for i in range(len(userData["tokens"])):
            token = userData["tokens"][i]
            amount = userData["cumulativeAmounts"][i]
            # print(user, token, amount)
            result.increase_user_rewards(user, token, int(amount))

    # result.printState()
    return result


def combine_rewards(list, cycle, badgerTree):
    totals = RewardsList(cycle, badgerTree)
    total = 0
    # For each rewards list entry
    for key, rewardsSet in list.items():
        # Get the claims data
        # claims = rewardsSet["claims"]
        for user, userData in rewardsSet.claims.items():
            # For each token
            for token, tokenAmount in userData.items():
                totals.increase_user_rewards(user, token, tokenAmount)
                total += tokenAmount
    totals.badgerSum = total
    # totals.printState()
    return totals


def guardian(badger: BadgerSystem, startBlock, endBlock, test=False):
    """
    Guardian Role
    - Check if there is a new proposed root
    - If there is, run the rewards script at the same block height to verify the results
    - If there is a discrepency, notify admin

    (In case of a one-off failure, Script will be attempted again at the guardianInterval)
    """

    print("Guardian", startBlock, endBlock)

    badgerTree = badger.badgerTree
    guardian = badger.guardian
    nextCycle = getNextCycle(badger)

    console.print("\n[bold cyan]===== Guardian =====[/bold cyan]\n")

    if not badgerTree.hasPendingRoot():
        console.print("[bold yellow]===== Result: No Pending Root =====[/bold yellow]")
        return False

    currentMerkleData = fetchCurrentMerkleData(badger)
    currentRewards = fetch_current_rewards_tree(badger)
    currentContentHash = currentMerkleData["contentHash"]
    # blockNumber = currentMerkleData["blockNumber"]

    console.print("\n[bold cyan]===== Verifying Rewards =====[/bold cyan]\n")
    print("Geyser Rewards", startBlock, endBlock, nextCycle)
    geyserRewards = calc_geyser_rewards(badger, startBlock, endBlock, nextCycle)

    newRewards = geyserRewards

    cumulativeRewards = process_cumulative_rewards(currentRewards, newRewards)

    # Take metadata from geyserRewards
    console.print("Processing to merkle tree")
    merkleTree = rewards_to_merkle_tree(
        cumulativeRewards, startBlock, endBlock, geyserRewards
    )

    # ===== Re-Publish data for redundancy ======
    rootHash = hash(merkleTree["merkleRoot"])
    contentFileName = content_hash_to_filename(rootHash)

    pendingMerkleData = badgerTree.getPendingMerkleData()

    assert pendingMerkleData["root"] == merkleTree["merkleRoot"]
    assert pendingMerkleData["contentHash"] == rootHash

    console.log(
        {
            "merkleRoot": merkleTree["merkleRoot"],
            "rootHash": str(rootHash),
            "contentFile": contentFileName,
            "startBlock": startBlock,
            "endBlock": endBlock,
            "currentContentHash": currentContentHash,
        }
    )

    print("Uploading to file " + contentFileName)

    # TODO: Upload file to AWS & serve from server
    with open(contentFileName, "w") as outfile:
        json.dump(merkleTree, outfile)
    # upload(contentFileName)

    with open(contentFileName) as f:
        after_file = json.load(f)

    compare_rewards(
        badger, startBlock, endBlock, currentRewards, after_file, currentContentHash
    )

    console.print("===== Guardian Complete =====")

    if not test:
        upload(contentFileName),
        badgerTree.approveRoot(
            merkleTree["merkleRoot"],
            rootHash,
            merkleTree["cycle"],
            {"from": guardian, "gas_price": gas_strategy},
        )


def fetchCurrentMerkleData(badger):
    currentMerkleData = badger.badgerTree.getCurrentMerkleData()
    root = str(currentMerkleData[0])
    contentHash = str(currentMerkleData[1])
    lastUpdateTime = currentMerkleData[2]
    blockNumber = badger.badgerTree.lastPublishBlockNumber()

    return {
        "root": root,
        "contentHash": contentHash,
        "lastUpdateTime": lastUpdateTime,
        "blockNumber": int(blockNumber),
    }


def getNextCycle(badger):
    return badger.badgerTree.currentCycle() + 1


def hash(value):
    return web3.toHex(web3.keccak(text=value))


def fetch_current_rewards_tree(badger):
    # TODO Files should be hashed and signed by keeper to prevent tampering
    # TODO How will we upload addresses securely?
    # We will check signature before posting
    merkle = fetchCurrentMerkleData(badger)
    pastFile = "rewards-1-" + str(merkle["contentHash"]) + ".json"

    console.print(
        "[bold yellow]===== Loading Past Rewards " + pastFile + " =====[/bold yellow]"
    )

    with open(pastFile) as f:
        currentTree = json.load(f)

    # Invariant: File shoulld have same root as latest
    assert currentTree["merkleRoot"] == merkle["root"]

    lastUpdateOnChain = merkle["blockNumber"]
    lastUpdate = int(currentTree["endBlock"])

    print("lastUpdateOnChain ", lastUpdateOnChain, " lastUpdate ", lastUpdate)
    # Ensure file tracks block within 1 day of upload
    assert abs(lastUpdate - lastUpdateOnChain) < 6500

    # Ensure upload was after file tracked
    assert lastUpdateOnChain >= lastUpdate
    return currentTree


def rootUpdater(badger, startBlock, endBlock, test=False):
    """
    Root Updater Role
    - Check how much time has passed since the last published update
    - If sufficient time has passed, run the rewards script and p
    - If there is a discrepency, notify admin

    (In case of a one-off failure, Script will be attempted again at the rootUpdaterInterval)
    """
    badgerTree = badger.badgerTree
    keeper = badger.keeper
    nextCycle = getNextCycle(badger)

    assert keeper == badger.keeper

    console.print("\n[bold cyan]===== Root Updater =====[/bold cyan]\n")
    currentMerkleData = fetchCurrentMerkleData(badger)
    currentRewards = fetch_current_rewards_tree(badger)

    currentTime = chain.time()

    timeSinceLastupdate = currentTime - currentMerkleData["lastUpdateTime"]
    if timeSinceLastupdate < rewards_config.rootUpdateInterval and not test:
        console.print(
            "[bold yellow]===== Result: Last Update too Recent =====[/bold yellow]"
        )
        return False

    # if badgerTree.hasPendingRoot():
    #     console.print(
    #         "[bold yellow]===== Result: Pending Root Since Last Update =====[/bold yellow]"
    #     )
    #     return False
    print("Geyser Rewards", startBlock, endBlock, nextCycle)

    geyserRewards = calc_geyser_rewards(badger, startBlock, endBlock, nextCycle)
    # metaFarmRewards = calc_harvest_meta_farm_rewards(badger, startBlock, endBlock)
    newRewards = geyserRewards

    cumulativeRewards = process_cumulative_rewards(currentRewards, newRewards)

    # Take metadata from geyserRewards
    console.print("Processing to merkle tree")
    merkleTree = rewards_to_merkle_tree(
        cumulativeRewards, startBlock, endBlock, geyserRewards
    )

    # Publish data
    rootHash = hash(merkleTree["merkleRoot"])
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
    # TODO: Upload file to AWS & serve from server
    with open(contentFileName, "w") as outfile:
        json.dump(merkleTree, outfile)

    with open(contentFileName) as f:
        after_file = json.load(f)

    compare_rewards(
        badger,
        startBlock,
        endBlock,
        currentRewards,
        after_file,
        currentMerkleData["contentHash"],
    )
    console.print("===== Root Updater Complete =====")
    if not test:
        upload(contentFileName)
        badgerTree.proposeRoot(
            merkleTree["merkleRoot"],
            rootHash,
            merkleTree["cycle"],
            {"from": keeper, "gas_price": gas_strategy},
        )

    return True


def watchdog(badger, endBlock):
    """
    Watchdog
    Ensure that the root has been updated within the maximum interval
    If not, the system is not functioning properly, notify admin
    """
    return False


def run_action(badger, args, test):
    if args["action"] == "rootUpdater":
        return rootUpdater(badger, args["startBlock"], args["endBlock"], test)
    if args["action"] == "guardian":
        return guardian(badger, args["startBlock"], args["endBlock"], test)
    if args["action"] == "watchdog":
        return watchdog(badger)
    return False


def content_hash_to_filename(contentHash):
    return "rewards-" + str(chain.id) + "-" + str(contentHash) + ".json"


def load_content_file(contentHash):
    fileName = content_hash_to_filename(contentHash)
    f = open(fileName,)
    return json.load(f)
