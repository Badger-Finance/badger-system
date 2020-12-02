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


def sum_rewards(rewardsList, cycle):
    """
    Sum rewards from all given set of rewards' list, returning a single rewards list
    """
    totals = RewardsList(cycle)

    # For each rewards list entry
    for key, rewardsSet in rewardsList.items():
        # Get the claims data
        claims = rewardsSet["claims"]
        for user, userData in claims.items():
            # For each token
            for token, tokenAmount in userData.items():
                totals.increase_user_rewards(user, token, tokenAmount)
    totals.printState()
    return totals


def calc_geyser_rewards(badger, startBlock, endBlock, cycle):
    """
    Calculate rewards for each geyser, and sum them
    userRewards = (userShareSeconds / totalShareSeconds) / tokensReleased
    (For each token, for the time period)
    """
    rewardsByGeyser = {}

    # For each Geyser, get a list of user to weights
    for key, geyser in badger.geysers.items():
        geyserRewards = calc_geyser_stakes(
            geyser, badger.globalStartBlock, startBlock, endBlock
        )
        rewardsByGeyser[key] = geyserRewards

    console.log("rewardsByGeyser", rewardsByGeyser)
    return sum_rewards(rewardsByGeyser, cycle)


def calc_harvest_meta_farm_rewards(badger, startBlock, endBlock):
    # TODO: Add harvest rewards
    return RewardsList()


def calc_early_contributor_rewards(badger, startBlock, endBlock):
    # TODO: Add earky contributor rewards
    return False


def guardian(badger, endBlock):
    """
    Guardian Role
    - Check if there is a new proposed root
    - If there is, run the rewards script at the same block height to verify the results
    - If there is a discrepency, notify admin

    (In case of a one-off failure, Script will be attempted again at the guardianInterval)
    """
    # badgerTree = badger.badgerTree
    # guardian = badgerTree.getRoleMember(GUARDIAN_ROLE, 0)
    # # TODO prod: accounts.add(private_key=ENV Variable)
    # assert guardian == badger.guardian

    # # Check latest root proposal
    # proposed = badgerTree.getPendingMerkleData()
    # nextCycle = badgerTree.currentCycle() + 1

    # console.log(proposed, nextCycle)

    # badger.badgerTree.approveRoot(
    #     proposed[0], proposed[1], nextCycle, {"from": guardian}
    # )
    # chain.mine()

    # merkleContent = load_content_file(proposed[1])

    badgerTree = badger.badgerTree
    guardian = badger.guardian

    console.print("\n[bold cyan]===== Guardian =====[/bold cyan]\n")

    hasPendingRoot = badgerTree.hasPendingRoot()
    if not hasPendingRoot:
        console.print("[bold yellow]===== Result: No Pending Root =====[/bold yellow]")
        return False

    pendingMerkleData = badgerTree.getPendingMerkleData()
    nextCycle = badgerTree.currentCycle() + 1

    startBlock = max(badger.globalStartBlock, badgerTree.lastPublishBlockNumber() + 1)
    endBlock = pendingMerkleData[3]

    console.log("pendingMerkleData", pendingMerkleData)

    geyserRewards = calc_geyser_rewards(badger, startBlock, endBlock, nextCycle)
    # metaFarmRewards = calc_harvest_meta_farm_rewards(badger, startBlock, endBlock)
    # earlyContributorRewards = calc_early_contributor_rewards(badger, startBlock, endBlock)

    totalRewards = geyserRewards
    merkleTree = rewards_to_merkle_tree(totalRewards)

    # Publish data
    rootHash = web3.toHex(web3.keccak(text=merkleTree["merkleRoot"]))
    badger.badgerTree.approveRoot(
        merkleTree["merkleRoot"], rootHash, merkleTree["cycle"], {"from": guardian}
    )
    chain.mine()

    contentFileName = content_hash_to_filename(rootHash)


def rootUpdater(badger, endBlock):
    """
    Root Updater Role
    - Check how much time has passed since the last published update
    - If sufficient time has passed, run the rewards script and p
    - If there is a discrepency, notify admin

    (In case of a one-off failure, Script will be attempted again at the rootUpdaterInterval)
    """
    badgerTree = badger.badgerTree
    keeper = badger.keeper
    guardian = badger.guardian
    currentMerkleData = badgerTree.getCurrentMerkleData()
    nextCycle = badgerTree.currentCycle() + 1

    console.print("\n[bold cyan]===== Root Updater =====[/bold cyan]\n")

    console.log("currentMerkleData", currentMerkleData)
    lastUpdateTime = currentMerkleData[2]
    blockNumber = currentMerkleData[3]

    currentTime = chain.time()

    timeSinceLastupdate = currentTime - lastUpdateTime
    if timeSinceLastupdate < rewards_config.rootUpdateInterval:
        console.print(
            "[bold yellow]===== Result: Last Update too Recent =====[/bold yellow]"
        )
        return False

    # Start after the previous snapshot, or globalStartBlock
    startBlock = max(badger.globalStartBlock, blockNumber + 1)

    geyserRewards = calc_geyser_rewards(badger, startBlock, endBlock, nextCycle)
    # metaFarmRewards = calc_harvest_meta_farm_rewards(badger, startBlock, endBlock)
    # earlyContributorRewards = calc_early_contributor_rewards(badger, startBlock, endBlock)

    totalRewards = geyserRewards
    merkleTree = rewards_to_merkle_tree(totalRewards)

    # Publish data
    rootHash = web3.toHex(web3.keccak(text=merkleTree["merkleRoot"]))
    badger.badgerTree.proposeRoot(
        merkleTree["merkleRoot"], rootHash, merkleTree["cycle"], {"from": keeper}
    )

    chain.mine()
    contentFileName = content_hash_to_filename(rootHash)

    print(
        {
            "merkleRoot": merkleTree["merkleRoot"],
            "rootHash": str(rootHash),
            "contentFile": contentFileName,
        }
    )

    print("Uploading to file " + contentFileName)

    # TODO: Upload file to AWS & serve from server
    with open(contentFileName, "w") as outfile:
        json.dump(merkleTree, outfile)
    upload(contentFileName)
    return True


def rootUpdaterMock(badger, endBlock):
    mockData = {
        "0x66ab6d9362d4f35596279692f0251db635165871": 85626748830336749923869,
        "0xDA25ee226E534d868f0Dd8a459536b03fEE9079b": 144964735957825140271492,
        "0x33A4622B82D4c04a53e170c638B944ce27cffce3": 56626748830336749923869,
        "0xe7bab002A39f9672a1bD0E949d3128eeBd883575": 45301378029056871262233,
        "0x482c741b0711624d1f462E56EE5D8f776d5970dC": 36241085595479651240806,
    }

    token = "0x3472A5A71965499acd81997a54BBA8D852C6E53d"

    rewards = RewardsList(1)
    for user, amount in mockData.items():
        rewards.increase_user_rewards(user, token, amount)

    merkleTree = rewards_to_merkle_tree(rewards)
    rootHash = web3.toHex(web3.keccak(text=merkleTree["merkleRoot"]))

    contentFileName = content_hash_to_filename(rootHash)

    # TODO: Upload file to AWS & serve from server
    with open(contentFileName, "w") as outfile:
        json.dump(merkleTree, outfile)
    upload(contentFileName)
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
        return rootUpdater(badger, args["endBlock"])
    if args["action"] == "guardian":
        return guardian(badger, args["endBlock"])
    if args["action"] == "watchdog":
        return watchdog(badger)
    return False


def main(args):
    # Load Badger system from config
    badger = connect_badger("local.json")

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

