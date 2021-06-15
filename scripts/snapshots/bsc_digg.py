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
    bDiggLpAddress = "0xa861Ba302674b08f7F2F24381b705870521DDfed".lower()

    bDiggHolders = fetch_wallet_balances(1, 1, None, block, chain="bsc")[1]

    bDiggLpHolders = fetch_sett_balances(
        "",
        bDiggLpAddress,
        block,
        chain="bsc"
    )
    return bDiggHolders, bDiggLpHolders


def main():
    block0Eth = 123
    block1Eth = 400

    block0Bsc = 1234
    block1Bsc = 1235

    bDiggEth0, diggUlp, diggSlp0 = get_ethereum_data(block0Eth)
    bDiggEth1, diggUlp1, diggSlp1 = get_ethereum_data(block1Eth)

    bdiggBsc0, bdiggLpBsc0 = get_bsc_data(block0Bsc)
    bdiggBsc1, bdiggLpBsc1 = get_bsc_data(block1Bsc)
    
    


def json2csv(name, old, new):
    addrs = set(old.keys()) + set(new.keys())
    with open("{}.csv".format(name)) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        csv_reader.writerow(["address, balance_at_t0, balance_at_t1"])
        for addr in addrs:
            csv_reader.writerow([
                addr,
                old.get(addr, 0),
                new.get(addr, 1)]
            )
