import time

from brownie import *
from tqdm import tqdm
from config.badger_config import badger_config
from rich.console import Console
from scripts.systems.badger_system import connect_badger

from assistant.rewards.rewards_assistant import calc_harvest_meta_farm_rewards
from assistant.subgraph.client import fetch_harvest_farm_events
from assistant.rewards.RewardsList import RewardsList

console = Console()


def main():
    badger = connect_badger(badger_config.prod_json)

    # Get latest block rewards were updated
    currentMerkleData = badger.badgerTree.getCurrentMerkleData()
    console.log("currentMerkleData", currentMerkleData)

    print("Run at", int(time.time()))

    latestBlock = chain.height
    harvestEvents = fetch_harvest_farm_events()
    rewards = RewardsList(0,badger.badgerTree)
    startBlock = 11376266
    endBlock = int(harvestEvents[0]["blockNumber"])
    console.log( sum ( [ int( h["farmToRewards"] ) for h in harvestEvents ] )/1e18)
    totalHarvested = 0
    for i in tqdm(range(len(harvestEvents))):
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
            rewards.increase_user_rewards(user.address,"FARM",farmUnit * user.shareSeconds/1e18)

        if i+1 > len(harvestEvents):
            startBlock = int(harvestEvent["blockNumber"])
            endBlock = int(harvestEvents[i+1]["blockNumber"])

    console.log(rewards.claims)
    console.log(sorted( [list(v.values())[0] for v in list(rewards.claims.values())  ] ))
        



