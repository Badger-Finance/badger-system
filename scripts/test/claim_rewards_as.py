from helpers.time_utils import days
import os
import json
from scripts.systems.badger_system import connect_badger
import warnings
from tabulate import tabulate
from brownie import *
from helpers.registry import registry

warnings.simplefilter("ignore")
# keeper = accounts.load("keeper")

rewardsFile = (
    "rewards-1-0x5da9ee3f9424d85a599405f3375709481bcf49d39c757372ac52763f0491c4c1.json"
)


def main():
    fileName = "deploy-" + "final" + ".json"
    badger = connect_badger(fileName)
    token = badger.token
    tree = badger.badgerTree

    with open(rewardsFile) as f:
        merkleTree = json.load(f)

    users = ["0xe450058b0023047C78Ca50a32356dA27DF984734"]
    for user in users:
        accounts.at(user, force=True)
        claim = merkleTree["claims"][user]
        pre = badger.token.balanceOf(user)
        print(pre)
        encoded = tree.claim.encode_input(
            claim["tokens"],
            claim["cumulativeAmounts"],
            claim["index"],
            claim["cycle"],
            claim["proof"],
        )
        print("encoded", encoded)
        tree.claim(
            claim["tokens"],
            claim["cumulativeAmounts"],
            claim["index"],
            claim["cycle"],
            claim["proof"],
            {"from": user},
        )
        post = badger.token.balanceOf(user)
        print({"pre": pre, "post": post, "claim": claim["cumulativeAmounts"][0]})
        assert pre + claim["cumulativeAmounts"][0] == post
