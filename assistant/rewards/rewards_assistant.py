from assistant.rewards.rewards_checker import compare_rewards
from helpers.tx_utils import send
from helpers.time_utils import hours
from assistant.rewards.early_contributors import calc_early_contributor_rewards
import json
import boto3
from eth_utils.hexadecimal import encode_hex

from assistant.rewards.calc_stakes import calc_geyser_stakes
from assistant.rewards.config import rewards_config
from assistant.rewards.merkle_tree import rewards_to_merkle_tree
from brownie import *
from dotmap import DotMap
from helpers.constants import EmptyBytes32, GUARDIAN_ROLE
from rich.console import Console
from scripts.systems.badger_system import connect_badger
from eth_abi.packed import encode_abi_packed
from assistant.rewards.script_config import env_config
from assistant.rewards.RewardsList import RewardsList

console = Console()

globalStartBlock = 11381158


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


def guardian(badger, startBlock, endBlock, test=False):
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

    pendingMerkleData = badgerTree.getPendingMerkleData()

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
        upload(contentFileName)

        send(
            badgerTree,
            badgerTree.approveRoot.encode_input(
                merkleTree["merkleRoot"], rootHash, merkleTree["cycle"]
            ),
            "guardian",
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
    # Ensure file tracks block within 100 of previous upload
    assert abs(lastUpdate - lastUpdateOnChain) < 100

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
    if timeSinceLastupdate < hours(1.8):
        console.print(
            "[bold yellow]===== Result: Last Update too Recent =====[/bold yellow]"
        )
        return False

    if badgerTree.hasPendingRoot():
        console.print(
            "[bold yellow]===== Result: Pending Root Since Last Update =====[/bold yellow]"
        )
        return False
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
        send(
            badgerTree,
            badgerTree.proposeRoot.encode_input(
                merkleTree["merkleRoot"], rootHash, merkleTree["cycle"]
            ),
            "keeper",
        )

    return True


def watchdog(badger, endBlock):
    """
    Watchdog
    Ensure that the root has been updated within the maximum interval
    If not, the system is not functioning properly, notify admin
    """
    return False


def run_action(badger, args):
    if args["action"] == "rootUpdater":
        return rootUpdater(badger, args["startBlock"], args["endBlock"])
    if args["action"] == "guardian":
        return guardian(badger, args["startBlock"], args["endBlock"])
    if args["action"] == "watchdog":
        return watchdog(badger)
    return False


def main(args):
    # Load Badger system from config
    badger = connect_badger("deploy-1.json")

    # Attempt node connection.
    # If primary fails, try the backup
    # If backup fails, notify admin
    # Script will be run again at the defined interval

    # Determine start block and end block
    # Start block = Min(globalStartBlock, lastUpdateBlock+1)
    # If ETH block height < startBlock, fail

    # run_action(badger, args)

    # merkle_allocations = DotMap()

    # # Determine how many tokens of each type should be distributed during this time / block interval using unlockSchedules from all

    # pools = [
    #     badger.pools.sett.native.renCrv,
    #     badger.pools.sett.native.sbtcCrv,
    #     badger.pools.sett.native.tbtcCrv,
    #     badger.pools.sett.pickle.renCrv,
    #     badger.pools.sett.harvest.renCrv,
    # ]

    # for geyser in pools:
    #     distributions = calc_geyser_distributions(geyser, startBlock, endBlock)
    #     stakeWeights = calc_geyser_stakes(
    #         geyser, config.globalStartBlock, startBlock, endBlock
    #     )
    #     allocations = add_allocations(distributions, stakeWeights)

    # Confirm that totals don't exceed the expected - one safeguard against expensive invalid roots on the non-contract side


def content_hash_to_filename(contentHash):
    return "rewards-" + str(chain.id) + "-" + str(contentHash) + ".json"


def load_content_file(contentHash):
    fileName = content_hash_to_filename(contentHash)
    f = open(fileName,)
    return json.load(f)


def upload(fileName):
    upload_bucket = "badger-json"
    upload_file_key = "rewards/" + fileName
    name = "rewards-1337-<hash>.json"

    # f = open(fileName,)
    # contentFile = json.load(f)

    print("Uploading file to s3/" + upload_file_key)

    s3 = boto3.client(
        "s3",
        aws_access_key_id=env_config.aws_access_key_id,
        aws_secret_access_key=env_config.aws_secret_access_key,
    )
    s3.upload_file(fileName, upload_bucket, upload_file_key)


def confirmUpload(fileName):
    upload_bucket = "badger-json"
    upload_file_key = "rewards/" + fileName
    name = "rewards-1337-<hash>.json"

    # f = open(fileName,)
    # contentFile = json.load(f)

    print("Uploading file to s3/" + upload_file_key)

    s3 = boto3.client(
        "s3",
        aws_access_key_id=env_config.aws_access_key_id,
        aws_secret_access_key=env_config.aws_secret_access_key,
    )
    s3.read(fileName, upload_bucket, upload_file_key)
