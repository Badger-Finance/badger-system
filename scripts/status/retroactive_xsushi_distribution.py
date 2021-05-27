import json

from brownie import *
from tqdm import tqdm
from config.badger_config import badger_config
from rich.console import Console
from scripts.systems.badger_system import connect_badger
from assistant.rewards.classes.RewardsList import RewardsList
from config.rewards_config import rewards_config
from brownie.network.gas.strategies import GasNowStrategy
from assistant.rewards.classes.MerkleTree import rewards_to_merkle_tree
from assistant.rewards.classes.RewardsLog import rewardsLog
from assistant.rewards.rewards_assistant import fetch_current_rewards_tree
from assistant.rewards.rewards_utils import process_cumulative_rewards
from assistant.rewards.meta_rewards.sushi import calc_all_sushi_rewards

gas_strategy = GasNowStrategy("fast")
console = Console()


def main():
    test = True
    badger = connect_badger(badger_config.prod_json, load_deployer=False)
    nextCycle = badger.badgerTree.currentCycle() + 1
    startBlock = 0
    endBlock = chain.height
    rewards = calc_all_sushi_rewards(
        badger, startBlock, endBlock, nextCycle, retroactive=True
    )
    rewardsLog.save("retroactive-xsushi")
    currentRewards = fetch_current_rewards_tree(badger)

    cumulative_rewards = process_cumulative_rewards(currentRewards, rewards)
    merkleTree = rewards_to_merkle_tree(cumulative_rewards, startBlock, endBlock, {})
    rootHash = web3.toHex(web3.keccak(text=merkleTree["merkleRoot"]))

    contentFileName = (
        "rewards-" + str(chain.id) + "-" + str(merkleTree["merkleRoot"]) + ".json"
    )
    console.log("Saving merkle tree as {}".format(contentFileName))
    with open(contentFileName, "w") as f:
        json.dump(merkleTree, f, indent=4)

    if not test:
        badger.badgerTree.proposeRoot(
            merkleTree["merkleRoot"],
            rootHash,
            nextCycle,
            {"from": badger.keeper, "gas_price": gas_strategy},
        )

        badger.badgerTree.approveRoot(
            merkleTree["merkleRoot"],
            rootHash,
            nextCycle,
            {"from": badger.keeper, "gas_price": gas_strategy},
        )
