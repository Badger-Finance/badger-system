from brownie import *
from tqdm import tqdm
from config.badger_config import badger_config
from rich.console import Console
from scripts.systems.badger_system import connect_badger
import json
from assistant.rewards.rewards_assistant import calc_sushi_rewards, process_cumulative_rewards, fetch_current_rewards_tree
from assistant.rewards.rewards_checker import test_claims
from assistant.subgraph.client import fetch_harvest_farm_events
from assistant.rewards.RewardsList import RewardsList
from config.rewards_config import rewards_config
from brownie.network.gas.strategies import GasNowStrategy
from assistant.rewards.merkle_tree import rewards_to_merkle_tree
from assistant.rewards.RewardsLogger import rewardsLogger

gas_strategy = GasNowStrategy("fast")
console = Console()

def hash(value):
    return web3.toHex(web3.keccak(text=value))

def main():
    test = True
    badger = connect_badger(badger_config.prod_json, load_deployer=False)
    nextCycle = badger.badgerTree.currentCycle() + 1

    startBlock = 12593628
    endBlock = chain.height

    currentRewards = fetch_current_rewards_tree(badger)

    console.log(currentRewards["startBlock"])
    console.log(currentRewards["endBlock"])

    rewards = calc_sushi_rewards(
        badger, startBlock, endBlock, nextCycle)
    rewardsLogger.save("retroactive-xsushi")

    cumulative_rewards = process_cumulative_rewards(currentRewards, rewards)
    merkleTree = rewards_to_merkle_tree(
        cumulative_rewards, startBlock, endBlock, {})
    rootHash = web3.toHex(web3.keccak(text=merkleTree["merkleRoot"]))

    contentFileName = "rewards-" + \
        str(chain.id) + "-" + str(rootHash) + ".json"
    console.log("Saving merkle tree as {}".format(contentFileName))
    with open(contentFileName, "w") as f:
        json.dump(merkleTree, f, indent=4)

    if not test:
        badger.badgerTree.proposeRoot(
            merkleTree["merkleRoot"],
            rootHash,
            nextCycle,
            {"from": badger.keeper, "gas_price": gas_strategy},
            currentRewards["startBlock"],
            currentRewards["endBlock"]
        )

        badger.badgerTree.approveRoot(
            merkleTree["merkleRoot"],
            rootHash,
            nextCycle,
            {"from": badger.keeper, "gas_price": gas_strategy},
            currentRewards["startBlock"],
            currentRewards["endBlock"]
        )
