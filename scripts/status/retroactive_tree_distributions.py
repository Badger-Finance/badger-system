from brownie import *
import json
from tqdm import tqdm
from config.badger_config import badger_config
from rich.console import Console
from scripts.systems.badger_system import connect_badger
from assistant.rewards.rewards_assistant import fetch_current_rewards_tree
from assistant.rewards.rewards_utils import process_cumulative_rewards
from assistant.rewards.meta_rewards.tree_rewards import calc_tree_rewards
from assistant.rewards.rewards_checker import test_claims
from assistant.rewards.classes.RewardsList import RewardsList
from config.rewards_config import rewards_config
from brownie.network.gas.strategies import GasNowStrategy
from assistant.rewards.classes.MerkleTree import rewards_to_merkle_tree
from assistant.rewards.aws_utils import upload

gas_strategy = GasNowStrategy("fast")
console = Console()


def hash(value):
    return web3.toHex(web3.keccak(text=value))


def main():
    test = False
    badger = connect_badger(load_root_proposer=True)
    nextCycle = badger.badgerTree.currentCycle() + 1

    startBlock = 0
    endBlock = chain.height

    currentRewards = fetch_current_rewards_tree(badger)

    console.log(currentRewards["startBlock"])
    console.log(currentRewards["endBlock"])

    rewards = calc_tree_rewards(badger, startBlock, endBlock, nextCycle)

    cumulative_rewards = process_cumulative_rewards(currentRewards, rewards)
    merkleTree = rewards_to_merkle_tree(cumulative_rewards, startBlock, endBlock, {})
    rootHash = web3.toHex(web3.keccak(text=merkleTree["merkleRoot"]))

    contentFileName = "rewards-" + str(chain.id) + "-" + str(rootHash) + ".json"
    console.log("Saving merkle tree as {}".format(contentFileName))
    with open(contentFileName, "w") as f:
        json.dump(merkleTree, f, indent=4)

    if not test:
        badger.badgerTree.proposeRoot(
            merkleTree["merkleRoot"],
            rootHash,
            nextCycle,
            currentRewards["startBlock"],
            currentRewards["endBlock"],
            {"from": badger.root_proposer, "gas_price": gas_strategy},
        )

        upload(contentFileName, merkleTree, publish=False)
