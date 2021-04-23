from scripts.rewards.rewards_utils import calc_next_cycle_range
import time
import json
import matplotlib.pyplot as plt
from brownie import *
from config.badger_config import badger_config
from rich.console import Console
from scripts.systems.badger_system import connect_badger
from assistant.rewards.aws_utils import download_past_trees
from assistant.rewards.rewards_assistant import run_action

console = Console()
rewardsInfo = {}
tokens = {
    "Badger":"0x3472A5A71965499acd81997a54BBA8D852C6E53d",
    "XSushi":"0x8798249c2E607446EfB7Ad49eC89dD1865Ff4272",
    "Farm":"0xa0246c9032bC3A600820415aE600c6388619A14D",
}

def main():
    trees = download_past_trees(2)
    pastRewards = json.loads(trees[1])
    lastTree = json.loads(trees[0])

    badger = connect_badger(
        badger_config.prod_json, load_keeper=False, load_deployer=False
    )
    startBlock = int(lastTree["startBlock"])
    endBlock = int(lastTree["endBlock"])

    newTree = run_action(
        badger,
        {
            "action": "rootUpdater",
            "startBlock": startBlock,
            "endBlock": endBlock,
            "pastRewards": pastRewards,
        },
        test=True,
    )["merkleTree"]
    compare_trees(newTree, lastTree)
    
    x = ["{} Diff".format((t)) for t in tokens.keys() ]
    x_pos = [i for i, _ in enumerate(x)]
    diffs = []
    for addr,amount in rewardsInfo["old"]["tokenTotals"].items():
        if addr == "0x798D1bE841a82a273720CE31c822C61a67a601C3":
            continue
        diffs.append(
           (int(amount)/1e18) - (int(rewardsInfo["new"]["tokenTotals"][addr])/1e18)
        )
    plt.bar(x_pos, diffs, color='green')
    plt.xlabel("Token diffs")
    plt.ylabel("Diff amount")
    plt.title("Token diff vs last cycle")

    plt.xticks(x_pos, x)

    plt.savefig("logs/geyser_data.png")

    with open('logs/rewards-data.json', 'w') as fp:
        json.dump(rewardsInfo, fp, indent=4)


def compare_trees(current, previous):
    rewardsInfo["old"] = {
        "tokenTotals": previous["tokenTotals"]
    }
    rewardsInfo["new"] = {
        "tokenTotals": current["tokenTotals"]
    }
    rewardsInfo["diffs"] = {}
    console.log(len(previous["claims"]))
    console.log(len(current["claims"]))
    rewardsInfo["addressDiff"] = list(set(current["claims"].keys()) ^ set(previous["claims"].keys()))

    for addr,data in previous["claims"].items():
        if addr not in rewardsInfo["diffs"]:
            rewardsInfo["diffs"][addr] = {
                    "old":{},
                    "new":{}
                }
        for i in range(len(data["tokens"])):
            token = data["tokens"][i]
            amount = data["cumulativeAmounts"][i]
            rewardsInfo["diffs"][addr]["old"][token] = amount


    for addr,data in current["claims"].items():
        if addr not in rewardsInfo["diffs"]:
            rewardsInfo["diffs"][addr] = {
                "old":{},
                "new":{}
            }
        for i in range(len(data["tokens"])): 
            token = data["tokens"][i]
            amount = data["cumulativeAmounts"][i]
            rewardsInfo["diffs"][addr]["new"][token] = amount


    
