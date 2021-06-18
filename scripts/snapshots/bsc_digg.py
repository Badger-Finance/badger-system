import json
import csv
from assistant.subgraph.client import fetch_sett_balances, fetch_wallet_balances
from assistant.rewards.rewards_utils import calculate_sett_balances

from scripts.systems.badger_system import connect_badger

from brownie import *

badger = connect_badger()


def get_ethereum_data(block):
    bdiggHolders = calculate_sett_balances(
        badger,
        "native.digg",
        block
    )
    diggUlpHolders = calculate_sett_balances(
        badger,
        "native.uniDiggWbtc",
        block
    )
    diggSlpHolders = calculate_sett_balances(
        badger,
        "native.sushiDiggWbtc",
        block
    )
    return bdiggHolders, diggUlpHolders, diggSlpHolders


def get_bsc_data(block):
    bDiggLpAddress = "0xa861ba302674b08f7f2f24381b705870521ddfed".lower()
    bDiggLpHolders = fetch_sett_balances(
        "",
        bDiggLpAddress,
        block,
        chain="bsc"
    )

    bDiggHolders = fetch_wallet_balances(1, 1, None, block, chain="bsc")[1]

    return bDiggHolders, bDiggLpHolders


def main():

    block0Bsc = 7192108
    block1Bsc = 8381879
    bdiggBsc0, bdiggLpBsc0 = get_bsc_data(block0Bsc)
    bdiggBsc1, bdiggLpBsc1 = get_bsc_data(block1Bsc)
    
    json2csv("bDiggBSC",bdiggBsc0,bdiggBsc1)
    json2csv("bDiggLpBSC",bdiggLpBsc0,bdiggLpBsc1)
    
    


def json2csv(name, old, new):
    addrs = list(set(old.keys()).union(set(new.keys())))
    with open("bscData/{}.csv".format(name),"w") as csv_file:
        csv_writer = csv.writer(csv_file, delimiter=',')
        csv_writer.writerow(["address", "balance_at_t0", "balance_at_t1"])
        for addr in addrs:
            csv_writer.writerow([
                addr,
                old.get(addr, 0)/1e18,
                new.get(addr, 0)/1e18]
            )
