import time
import json

from brownie import *
from tqdm import tqdm
from config.badger_config import badger_config
from rich.console import Console
from scripts.systems.badger_system import connect_badger

from assistant.rewards.rewards_assistant import calc_harvest_meta_farm_rewards,process_cumulative_rewards,fetch_current_rewards_tree
from assistant.subgraph.client import fetch_harvest_farm_events
from assistant.rewards.RewardsList import RewardsList
from config.rewards_config import rewards_config
from brownie.network.gas.strategies import GasNowStrategy
from assistant.rewards.merkle_tree import rewards_to_merkle_tree


gas_strategy = GasNowStrategy("fast")
console = Console()


def main():
    badger = connect_badger(badger_config.prod_json)
    farmTokenAddress = "0xa0246c9032bC3A600820415aE600c6388619A14D"
    nextCycle = badger.badgerTree.currentCycle() + 1
    console.log(nextCycle)
    currentMerkleData = badger.badgerTree.getCurrentMerkleData()
    console.log(currentMerkleData)
    timeSinceLastUpdate = chain.time() - currentMerkleData[2]
    

    print("Run at", int(time.time()))

    latestBlock = chain.height
    harvestEvents = fetch_harvest_farm_events()
    rewards = RewardsList(nextCycle,badger.badgerTree)
    settStartBlock = 11376266
    startBlock = settStartBlock
    endBlock = int(harvestEvents[0]["blockNumber"])
    console.log( sum ( [ int( h["farmToRewards"] ) for h in harvestEvents ] )/1e18)
    totalHarvested = 0
    for i in tqdm(range(len(harvestEvents))):
        console.log("Processing between {} and {}".format(startBlock,endBlock))
        harvestEvent = harvestEvents[i]
        user_state = calc_harvest_meta_farm_rewards(badger,"harvest.renCrv",startBlock,endBlock)
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
            rewards.increase_user_rewards(user.address,farmTokenAddress,farmUnit * user.shareSeconds/1e18)

        if i+1 < len(harvestEvents):
            startBlock = int(harvestEvent["blockNumber"])
            endBlock = int(harvestEvents[i+1]["blockNumber"])

    console.log(rewards.claims)
    console.log(sorted( [list(v.values())[0] for v in list(rewards.claims.values())  ] ))
    console.log(totalHarvested)
    claimsHarvested = sum( [list(v.values())[0] for v in list(rewards.claims.values())])
    console.log(claimsHarvested)
    
    currentRewards = fetch_current_rewards_tree(badger)
    cumulative_rewards = process_cumulative_rewards(currentRewards,rewards)

    merkleTree = rewards_to_merkle_tree(cumulative_rewards,settStartBlock,endBlock,{})
    # Upload merkle tree
    rootHash = hash(merkleTree["merkleRoot"])
    console.log(merkleTree["merkleRoot"])
    console.log(rootHash)
    contentFileName = "rewards-" + str(chain.id) + "-" + str(merkleTree["merkleRoot"]) + ".json"
    console.log("Saving merkle tree as {}".format(contentFileName))
    with open(contentFileName,"w") as f:
        json.dump(merkleTree,f)

    badger.badgerTree.proposeRoot(
        merkleTree["merkleRoot"],
        rootHash,
        nextCycle,
        {"from" :badger.keeper,"gas_price":gas_strategy}
    )





