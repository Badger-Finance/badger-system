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

    claimAt = chain.height
    harvestEvents = fetch_harvest_farm_events()
    rewards = RewardsList(0,badger.badgerTree)
    startBlock = 11376266
    endBlock = int(harvestEvents[0]["blockNumber"])

    for i in tqdm(range(len(harvestEvents) - 1)):
        harvestEvent = harvestEvents[i]
        console.log(harvestEvent)
        user_state = calc_harvest_meta_farm_rewards(badger,"harvest.renCrv",startBlock,endBlock)
        if len(user_state) == 0:
            continue

        farmRewards = int(harvestEvent["farmToRewards"])
        totalShareSeconds = sum([u.shareSeconds for u in user_state])
        farmUnit = farmRewards/totalShareSeconds
        for user in user_state:
            rewards.increase_user_rewards(user.address,"FARM",farmUnit * user.shareSeconds)
        startBlock = int(harvestEvent["blockNumber"])
        endBlock = int(harvestEvents[i+1]["blockNumber"])

    console.log(rewards)


