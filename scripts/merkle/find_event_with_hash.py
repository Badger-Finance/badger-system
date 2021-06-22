from brownie import *
from scripts.systems.badger_system import connect_badger

def main():
    badger = connect_badger()
    BadgerTree = web3.eth.contract(
        "0x660802Fc641b154aBA66a62137e71f331B6d787A",
        abi=badger.badgerTree.abi
    )
    logs = BadgerTree.events.RootUpdated.getLogs(
        fromBlock=0,
        toBlock=12684687
    )
    for log in logs:
        contentHash = log["args"]["root"]
        ch = web3.toHex(contentHash)
        print(str(ch))


