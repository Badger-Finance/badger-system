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
        sett = badger.getSett(key)

        admin = badger.getProxyAdmin(sett)
        sett_impl = admin.getProxyImplementation(sett)
        sett_admin = admin.getProxyAdmin(sett)

        sett_type = badger.getSettType(key)

        print(key, sett_type)

        table = []

        table.append(["Sett Key", key])
        table.append(["Sett Type", sett_type])
        table.append(["Sett Logic", sett_impl])
        table.append(["Sett Admin", sett_admin])

        if sett_type == "v1":
            snap = SnapshotManager(badger, key)
            state = snap.snap()
            snap.printPermissions()
            # snap.printTable(state)
            strategy = badger.getStrategy(key)
            strategy_impl = badger.devProxyAdmin.getProxyImplementation(strategy)
            strategy_admin = admin.getProxyAdmin(strategy)
            table.append(["Strategy Logic", strategy_impl])
            table.append(["Strategy Admin", strategy_admin])

        print(tabulate(table, ["Key", "Value"]))
