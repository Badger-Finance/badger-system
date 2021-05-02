from brownie import *
from rich.console import Console
from config.badger_config import badger_config
from helpers.sett.SnapshotManager import SnapshotManager
from scripts.systems.badger_system import connect_badger
from tabulate import tabulate

console = Console()


def main():
    badger = connect_badger(badger_config.prod_json)
    console.print("\n[white]===== 🦡 Sett Status 🦡 =====[white]\n")
    for key in badger.sett_system.vaults.keys():
        snap = SnapshotManager(badger, key)
        state = snap.snap()
        snap.printPermissions()
        snap.printTable(state)
