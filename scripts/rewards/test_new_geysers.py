from scripts.rewards.rewards_utils import calc_next_cycle_range
import time
import json
from brownie import *
from config.badger_config import badger_config
from rich.console import Console
from scripts.systems.badger_system import connect_badger
from assistant.rewards.aws_utils import download_past_trees
from assistant.rewards.rewards_assistant import run_action

console = Console()
rewardsInfo = {}
def main():
    trees = download_past_trees(5)
    badger = connect_badger(
        badger_config.prod_json, load_keeper=False, load_deployer=False
    )
    for index, merkle in enumerate(trees):
        if index == (len(trees)- 1):
            break
        currentTree = json.loads(merkle)
        previousTree = json.loads(trees[index + 1])
        compare_trees(currentTree, previousTree)

        newRewardsTree = run_action(
            badger,
            {
                "action": "rootUpdater",
                "startBlock": int(currentTree["startBlock"]),
                "endBlock": int(currentTree["endBlock"]),
                "pastRewards": previousTree,
            },
            test=True,
        )["merkleTree"]
        compare_trees(newRewardsTree,previousTree)

    with open('logs/rewards-data.json', 'w') as fp:
        json.dump(rewardsInfo, fp,indent=4)


def compare_trees(current, previous):
    console.log("Comparing {} and {}".format(
        current["merkleRoot"],previous["merkleRoot"]
    ))
    rewardsKey = "{}-{}".format(
        current["merkleRoot"],
        previous["merkleRoot"]
    )
    rewardsInfo[rewardsKey] = {
        "diff":{},
        "startBlock":current["startBlock"],
        "endBlock":current["endBlock"],
    }

    assert previous["cycle"] < current["cycle"]
    for token, total in current["tokenTotals"].items():
        diff = total - previous["tokenTotals"][token]
        rewardsInfo[rewardsKey]["diff"][token] = int(diff)
        console.log("Diff of {} is {}".format(token, diff))
