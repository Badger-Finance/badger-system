from brownie import *
from rich.console import Console
from config.badger_config import badger_config
from helpers.sett.SnapshotManager import SnapshotManager
from scripts.systems.badger_system import connect_badger
from tabulate import tabulate

console = Console()

class ContractEntry:
    def __init__(self, name, address):
        self.name = name
        self.address = address

def main():
    badger = connect_badger()

    contracts = [
        ContractEntry('badgerRewardsManager', badger.badgerRewardsManager),
        ContractEntry('badgerTree', badger.badgerTree),
        ContractEntry('rewardsLogger', badger.rewardsLogger),
        ContractEntry('keeperAccessControl', badger.keeperAccessControl),
    ]
    
    table = []
    console.print("\n[white]===== Proxy Admin Checkup 🩺 =====[white]\n")
    for entry in contracts:
        admin = badger.getProxyAdmin(entry.address)
        table.append([entry.name, admin])
    
    print(tabulate(table, ["Key", "Value"]))
