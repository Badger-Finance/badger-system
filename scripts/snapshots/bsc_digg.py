import json
import csv
from assistant.subgraph.client import fetch_sett_balances, fetch_wallet_balances
from brownie import *


def main():
    blockStart = 6769850
    blockEnd = 7330670
    bDiggAddress = "0x5986d5c77c65e5801a5caa4fae80089f870a71da".lower()
    bDiggLpAddress = "0xa861Ba302674b08f7F2F24381b705870521DDfed".lower()
    print("here")
    bDiggStart = fetch_wallet_balances(1, 1, None, blockStart, chain="bsc")[1]
    print("here")

    bDiggLpStart = fetch_sett_balances(bDiggLpAddress, blockStart, chain="bsc")

    bDiggEnd = fetch_wallet_balances(1, 1, None, blockEnd, chain="bsc")[1]

    bDiggLpEnd = fetch_sett_balances(bDiggLpAddress, blockEnd, chain="bsc")

    json2csv(bDiggStart, "bDiggStart")
    json2csv(bDiggLpStart, "bDiggLpStart")
    json2csv(bDiggEnd, "bDiggCurrent")
    json2csv(bDiggLpEnd, "bDiggLpEnd")


def json2csv(data, fileName):
    for addr, value in data.items():
        if value < 0:
            data[addr] = 0

    with open("bscData/{}.csv".format(fileName), "w") as f:
        writer = csv.writer(f, delimiter=",")
        writer.writerow(["address", "value"])
        writer.writerows(zip(data.keys(), data.values()))
