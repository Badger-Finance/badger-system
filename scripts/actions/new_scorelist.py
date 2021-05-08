import json
from scripts.systems.badger_system import BadgerSystem, connect_badger
from assistant.rewards.rewards_utils import calculate_sett_balances, combine_balances
from brownie import *


def main():
    badger = connect_badger("deploy-final.json")
    setts = [
        "native.renCrv",
        "native.sbtcCrv",
        "native.renCrv",
        "harvest.renCrv",
        "yearn.wbtc",
        "native.sushiWbtcEth",
    ]
    block = 12382594
    old_scores = json.load(open("scores.json"))
    for addr, scoreInfo in old_scores.items():
        for cond, amount in scoreInfo.items():
            if cond == "cond5":
                scoreInfo[cond] = 2

    vaultDepositers = []
    for s in setts:
        balances = calculate_sett_balances(badger, s, block)
        for user in balances:
            if user.balance > 0:
                vaultDepositers.append(web3.toChecksumAddress(user.address))

    for addr in vaultDepositers:
        if addr not in old_scores.keys():
            old_scores[addr] = {"cond8": 2}
        else:
            old_scores[addr]["cond8"] = 2
    threeList = []
    fourList = []
    for addr, info in old_scores.items():
        totalScore = sum(info.values())
        if totalScore >= 3:
            threeList.append(addr)
        if totalScore >= 4:
            fourList.append(addr)

    print(len(threeList))
    print(len(fourList))

    with open("scores,json", "w") as fp:
        json.dump(old_scores, fp)

    with open("final_list.json", "w") as fp2:
        json.dump(fourList, fp2)
