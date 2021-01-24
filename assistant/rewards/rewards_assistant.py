import json

from tqdm import tqdm
from assistant.rewards.calc_stakes import calc_geyser_stakes
from assistant.rewards.calc_harvest import calc_balances_from_geyser_events,get_initial_user_state
from assistant.subgraph.client import (
    fetch_sett_balances,
    fetch_geyser_events,
    fetch_sett_transfers,
    fetch_harvest_farm_events,
    fetch_sushi_harvest_events
)
from assistant.rewards.User import User
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

def calc_sushi_rewards(badger,startBlock,endBlock,nextCycle,retroactive):
    xSushiTokenAddress = "0x8798249c2e607446efb7ad49ec89dd1865ff4272"
    sushi_harvest_events = fetch_sushi_harvest_events()

    def filter_events(e):
        return int(e["blockNumber"]) > startBlock and int(e["blockNumber"]) < endBlock

    wbtcEthEvents = list(filter(filter_events,sushi_harvest_events["wbtcEth"]))
    wbtcBadgerEvents = list(filter(filter_events,sushi_harvest_events["wbtcBadger"]))
    totalxSushi = sum([int(e["toBadgerTree"]) for e in wbtcEthEvents]) + sum([int(e["toBadgerTree"]) for e in wbtcBadgerEvents])


    console.log(wbtcEthEvents)
    console.log(wbtcBadgerEvents)
    


    wbtcEthStartBlock = get_latest_event_block(wbtcEthEvents[0],sushi_harvest_events["wbtcEth"])
    if wbtcEthStartBlock == -1 or retroactive:
        wbtcEthStartBlock = 11537600

    console.log(wbtcEthStartBlock)
        
    console.log("Processing {} wbtcEth sushi events".format(len(wbtcEthEvents)))
    wbtcEthRewards = process_sushi_events(
        badger,wbtcEthStartBlock,endBlock,wbtcEthEvents,"native.sushiWbtcEth",nextCycle) 

    wbtcBadgerStartBlock = get_latest_event_block(wbtcBadgerEvents[0],sushi_harvest_events["wbtcBadger"])
    if wbtcBadgerEvents == -1 or retroactive:
        wbtcBadgerStartBlock = 11539529

    console.log(wbtcBadgerStartBlock)
    
    console.log("Processing {} wbtcBadger sushi events".format(len(wbtcBadgerEvents)))
    wbtcBadgerRewards = process_sushi_events(
        badger,wbtcBadgerStartBlock,endBlock,wbtcBadgerEvents,"native.sushiBadgerWbtc",nextCycle)

    # TODO: Add digg sushi strategy

    finalRewards = combine_rewards([wbtcEthRewards,wbtcBadgerRewards],nextCycle,badger.badgerTree)
    xSushiFromRewards = 0

    for user,claimData in finalRewards.claims.items():
        for token,tokenAmount in claimData.items():
            if token == xSushiTokenAddress:
                console.log("Address {}: {} xSushi".format(user,int(float(tokenAmount))/1e18 ))
                xSushiFromRewards += int(float(tokenAmount))

    console.log("Total xSushi {} from events".format(
        totalxSushi/1e18
    ))
    console.log("Total xSushi {} from claims".format(
        xSushiFromRewards/1e18
    ))
    difference = abs(totalxSushi - xSushiFromRewards)
    console.log("Difference {}".format(abs(totalxSushi/1e18 - xSushiFromRewards/1e18)))
    assert difference < 10000000
    return finalRewards

            
def process_sushi_events(badger,startBlock,endBlock,events,name,nextCycle):
    xSushiTokenAddress = "0x8798249c2e607446efb7ad49ec89dd1865ff4272"
    start = startBlock
    end = int(events[0]["blockNumber"])
    totalHarvested = 0
    rewards = RewardsList(nextCycle,badger.badgerTree)
    for i in tqdm(range(len(events))):
        xSushiRewards = int(events[i]["toBadgerTree"])
        user_state = calc_meta_farm_rewards(badger,name,start,end)
        console.log("Processing between blocks {} and {}, distributing {} to users".format(
            start,
            end,
            xSushiRewards/1e18
        ))
        totalHarvested += xSushiRewards/1e18
        console.print("{} total xSushi processed".format(totalHarvested))
        totalShareSeconds = sum([u.shareSeconds for u in user_state])
        xSushiUnit = xSushiRewards/totalShareSeconds
        for user in user_state:
            rewards.increase_user_rewards(user.address,xSushiTokenAddress,xSushiUnit * user.shareSeconds)

        if i+1 < len(events):
           start = int(events[i]["blockNumber"])
           end = int(events[i+1]["blockNumber"])

    console.log(sum([list(v.values())[0]/1e18 for v in list(rewards.claims.values())  ]))
    return rewards

def get_latest_event_block(firstEvent,harvestEvents):
    try:
        event_index = harvestEvents.index(firstEvent)
        console.log(event_index)
    except ValueError:
        return -1
    if event_index - 1 >= 0 and event_index - 1 < len(harvestEvents):
        # startBlock starts with the last harvest that happened 
        latestEvent = harvestEvents[event_index - 1] 
        return latestEvent["blockNumber"]
    else:
        return -1
    

def fetch_current_harvest_rewards(badger,startBlock,endBlock,nextCycle):
    farmTokenAddress = "0xa0246c9032bC3A600820415aE600c6388619A14D"
    harvestEvents = fetch_harvest_farm_events()
    rewards = RewardsList(nextCycle,badger.badgerTree)

    def filter_events(e):
        return int(e["blockNumber"]) > startBlock and int(e["blockNumber"]) < endBlock

    unprocessedEvents = list(filter(filter_events,harvestEvents))
    console.log("Processing {} farm events".format(len(unprocessedEvents)))

    if len(unprocessedEvents) == 0:
        return rewards

    start = get_latest_event_block(unprocessedEvents[0],harvestEvents)
    end = int(unprocessedEvents[0]["blockNumber"])
    totalHarvested = 0
    for i in tqdm(range(len(unprocessedEvents))):
        console.log("Processing between {} and {}".format(startBlock,endBlock))
        harvestEvent = unprocessedEvents[i]
        user_state = calc_meta_farm_rewards(badger,"harvest.renCrv",start,end)
        farmRewards = int(harvestEvent["farmToRewards"])
        console.print("Processing block {}, distributing {} to users".format(
            harvestEvent["blockNumber"],
            farmRewards/1e18,
         ))
        totalHarvested += farmRewards/1e18
        console.print("{} total FARM processed".format(totalHarvested))
        totalShareSeconds = sum([u.shareSeconds for u in user_state])
        farmUnit = farmRewards/totalShareSeconds
        for user in user_state:
            rewards.increase_user_rewards(user.address,farmTokenAddress,farmUnit * user.shareSeconds)

        if i+1 < len(unprocessedEvents):
            start = int(unprocessedEvents[i]["blockNumber"])
            end = int(unprocessedEvents[i+1]["blockNumber"])

    console.log(sorted( [list(v.values())[0]/1e18 for v in list(rewards.claims.values())  ] ))
    return rewards


def calc_meta_farm_rewards(badger,name, startBlock, endBlock):
    console.log("Calculating rewards between {} and {}".format(startBlock,endBlock))
    startBlockTime = web3.eth.getBlock(startBlock)["timestamp"]
    endBlockTime = web3.eth.getBlock(endBlock)["timestamp"]
    settId = badger.getSett(name).address.lower()
    geyserId = badger.getGeyser(name).address.lower()

    settBalances = fetch_sett_balances(settId, startBlock)
    settTransfers = fetch_sett_transfers(settId, startBlock, endBlock)
    # If there is nothing in the sett, and there have been no transfers
    if len(settBalances) == 0:
        if len(settTransfers) == 0:
            return []
    if len(settBalances) != 0:
        console.log("Found {} balances".format(len(settBalances)))
        console.log("Geyser amount in sett Balance: {}".format(settBalances[geyserId]/1e18))
        settBalances[geyserId] = 0

    geyserEvents = fetch_geyser_events(geyserId, startBlock)
    geyserBalances = calc_balances_from_geyser_events(geyserEvents)
    user_state = get_initial_user_state(
        settBalances, geyserBalances, startBlockTime
    )
    console.log("Processing {} transfers".format(len(settTransfers)))
    for transfer in settTransfers:
        transfer_address = transfer["account"]["id"]
        transfer_amount = int(transfer["amount"])
        transfer_timestamp = int(transfer["transaction"]["timestamp"])
        user = None
        for u in user_state:
            if u.address == transfer_address:
               user = u
        if user:
               user.process_transfer(transfer)
        else:
            # Prevent negative transfer from accumulated lp
            if transfer_amount < 0:
                transfer_amount = 0

            # If the user hasn't deposited before, create a new oneA
            user = User(transfer_address,transfer_amount,transfer_timestamp)
            user_state.append(user)

    for user in user_state:
        user.process_transfer({
            "transaction": {
                "timestamp": endBlockTime
            },
            "amount":0
        })
    
    totalShareSeconds = sum([u.shareSeconds for u in user_state])
    #for user in sorted(user_state,key=lambda u: u.shareSeconds,reverse=True):
    #    percentage = (user.shareSeconds/totalShareSeconds) * 100
    #    console.log(user,"{}%".format(percentage))

    return user_state



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


def combine_rewards(rewardsList,cycle, badgerTree):
    totals = RewardsList(cycle,badgerTree)
    for rewards in rewardsList:
        for user,claims in rewards.claims.items():
            for token,claim in claims.items():
                totals.increase_user_rewards(user,token,claim)
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
    # pastFile = "rewards-1-" + str(merkle["contentHash"]) + ".json"

    pastFile = "rewards-1-0xf5a8ede3b252cee8a1680f10a8f721ad21e336929b8be998bff5736371d3cb06.json"

    console.print(
        "[bold yellow]===== Loading Past Rewards " + pastFile + " =====[/bold yellow]"
    )

    # currentTree = json.loads(download(pastFile))
    with open(pastFile) as f:
        treeData = f.read()
    currentTree = json.loads(treeData)

    # Invariant: File shoulld have same root as latest
    # assert currentTree["merkleRoot"] == merkle["root"]

    lastUpdateOnChain = merkle["blockNumber"]
    lastUpdate = int(currentTree["endBlock"])

    print("lastUpdateOnChain ", lastUpdateOnChain, " lastUpdate ", lastUpdate)
    # Ensure file tracks block within 1 day of upload
    # assert abs(lastUpdate - lastUpdateOnChain) < 6500

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

    #timeSinceLastupdate = currentTime - currentMerkleData["lastUpdateTime"]
    #if timeSinceLastupdate < rewards_config.rootUpdateInterval and not test:
    #    console.print(
    #        "[bold yellow]===== Result: Last Update too Recent =====[/bold yellow]"
    #    )
    #    return False

    # if badgerTree.hasPendingRoot():
    #     console.print(
    #         "[bold yellow]===== Result: Pending Root Since Last Update =====[/bold yellow]"
    #     )
    #     return False
    print("Geyser Rewards", startBlock, endBlock, nextCycle)
    sushiRewards = calc_sushi_rewards(badger,startBlock,endBlock,nextCycle,retroactive=False)
    metaFarmRewards = fetch_current_harvest_rewards(badger,startBlock, endBlock,nextCycle)
    geyserRewards = calc_geyser_rewards(badger, startBlock, endBlock, nextCycle)
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
