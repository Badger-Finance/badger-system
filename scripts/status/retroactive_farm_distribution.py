import time
import json

from brownie import *
from tqdm import tqdm
from config.badger_config import badger_config
from rich.console import Console
from scripts.systems.badger_system import connect_badger

<<<<<<< Updated upstream
from assistant.rewards.rewards_assistant import calc_harvest_meta_farm_rewards,process_cumulative_rewards,fetch_current_rewards_tree
=======
from assistant.rewards.rewards_assistant import calc_meta_farm_rewards,process_cumulative_rewards,fetch_current_rewards_tree
>>>>>>> Stashed changes
from assistant.rewards.rewards_checker import test_claims
from assistant.subgraph.client import fetch_harvest_farm_events
from assistant.rewards.RewardsList import RewardsList
from config.rewards_config import rewards_config
from brownie.network.gas.strategies import GasNowStrategy
from assistant.rewards.merkle_tree import rewards_to_merkle_tree


gas_strategy = GasNowStrategy("fast")
console = Console()


def main():
    test = True
    badger = connect_badger(badger_config.prod_json)
    farmTokenAddress = "0xa0246c9032bC3A600820415aE600c6388619A14D"
    nextCycle = badger.badgerTree.currentCycle() + 1
    console.log("next cycle: {}".format(nextCycle))
    currentMerkleData = badger.badgerTree.getCurrentMerkleData()
    console.log(currentMerkleData)
    timeSinceLastUpdate = chain.time() - currentMerkleData[2]

    print("Run at", int(time.time()))

    latestBlock = chain.height
    harvestEvents = fetch_harvest_farm_events()
    rewards = RewardsList(nextCycle,badger.badgerTree)
<<<<<<< Updated upstream
=======
    console.log(rewards.claims)
>>>>>>> Stashed changes
    settStartBlock = 11376266
    startBlock = settStartBlock
    endBlock = int(harvestEvents[0]["blockNumber"])
    totalHarvested = 0
    for i in tqdm(range(len(harvestEvents))):
        console.log("Processing between {} and {}".format(startBlock,endBlock))
        harvestEvent = harvestEvents[i]
<<<<<<< Updated upstream
        user_state = calc_harvest_meta_farm_rewards(badger,"harvest.renCrv",startBlock,endBlock)
=======
        user_state = calc_meta_farm_rewards(badger,"harvest.renCrv",startBlock,endBlock)
>>>>>>> Stashed changes
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

        if i+1 < len(harvestEvents):
            startBlock = int(harvestEvent["blockNumber"])
            endBlock = int(harvestEvents[i+1]["blockNumber"])

    console.log(rewards.claims)
    console.log(sorted( [list(v.values())[0]/1e18 for v in list(rewards.claims.values())  ] ))
    claimsHarvested = sum( [list(v.values())[0] for v in list(rewards.claims.values())])
    
    currentRewards = fetch_current_rewards_tree(badger)
    cumulative_rewards = process_cumulative_rewards(currentRewards,rewards)

    merkleTree = rewards_to_merkle_tree(cumulative_rewards,settStartBlock,endBlock,{})
    # Upload merkle tree
    rootHash = web3.toHex(web3.keccak(text=merkleTree["merkleRoot"]))
    console.log(rootHash)
    contentFileName = "rewards-" + str(chain.id) + "-" + str(merkleTree["merkleRoot"]) + ".json"
    console.log("Saving merkle tree as {}".format(contentFileName))
    with open(contentFileName,"w") as f:
        json.dump(merkleTree,f,indent=4)


    farmHarvestedMerkleTree = 0
    claims = merkleTree["claims"]

    for user, claim in claims.items():
        if farmTokenAddress in claim["tokens"]:
            token_index = claim["tokens"].index(farmTokenAddress)
            amount = claim["cumulativeAmounts"][token_index]
            console.log("Address {} : {} FARM".format(user,int(float(amount))/1e18))
            farmHarvestedMerkleTree += int(float(amount))
            
    console.log("Total Farm Harvested {}".format(farmHarvestedMerkleTree/1e18))
    console.log("Claims Harvested From Events {}".format(claimsHarvested/1e18))

    console.log("Difference: {}".format((farmHarvestedMerkleTree/1e18) - (claimsHarvested/1e18)))
    difference = farmHarvestedMerkleTree - claimsHarvested
    console.log("Difference: {}".format(farmHarvestedMerkleTree - claimsHarvested))
    console.log(gas_strategy)
    if abs(difference) < 10000000 and not test:
        badger.badgerTree.proposeRoot(
        merkleTree["merkleRoot"],
        rootHash,
        nextCycle,
        {"from" :badger.keeper,"gas_price":gas_strategy})

        badger.badgerTree.approveRoot(
        merkleTree["merkleRoot"],
        rootHash,
        nextCycle,
        {"from" :badger.keeper,"gas_price":gas_strategy})

       

    





