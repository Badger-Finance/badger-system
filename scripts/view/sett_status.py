from brownie import *
from rich.console import Console
from config.badger_config import badger_config
from helpers.sett.SnapshotManager import SnapshotManager
from scripts.systems.badger_system import connect_badger
from tabulate import tabulate

console = Console()

setts_to_skip = [
    "native.badger",
    "native.renCrv",
    "native.sbtcCrv",
    "native.tbtcCrv",
    "native.uniBadgerWbtc",
    "harvest.renCrv",
    "native.sushiWbtcEth",
    "native.sushiBadgerWbtc",
    "native.digg",
    "native.uniDiggWbtc",
    "native.sushiDiggWbtc",
    "yearn.wbtc",
    "experimental.sushiIBbtcWbtc",
    "experimental.digg",
    "native.convexRenCrv",
    "native.convexSbtcCrv",
    "native.convexTbtcCrv",
    # "native.hbtcCrv",
    # "native.pbtcCrv",
    # "native.obtcCrv",
    # "native.bbtcCrv",
    # "native.tricrypto",
    # "native.cvxCrv",
    # "native.cvx"
]

def main():
    badger = connect_badger(badger_config.prod_json)
    console.print("\n[white]===== 🦡 Sett Status 🦡 =====[white]\n")
    for key in badger.sett_system.vaults.keys():
        if key in setts_to_skip:
            continue
        sett = badger.getSett(key)

        admin = badger.getProxyAdmin(sett)
        sett_impl = admin.getProxyImplementation(sett)
        sett_admin = admin.getProxyAdmin(sett)

        sett_type = badger.getSettType(key)

        print(key, sett_type)

        table = []

        console.print("[green]=== Admin: {} Sett ===[green]".format(key))
        table.append(["Sett Key", key])
        table.append(["Sett Type", sett_type])
        table.append(["Sett Logic", sett_impl])
        table.append(["Sett Admin", sett_admin])

        print(tabulate(table, ["Key", "Value"]))
        

        if sett_type == "v1":
            snap = SnapshotManager(badger, key)
            # state = snap.snap()
            
            # snap.printTable(state)

            if badger.hasStrategy(key):
                snap.printPermissions()
                strategy = badger.getStrategy(key)
                admin = badger.getProxyAdmin(strategy)
                strategy_impl = admin.getProxyImplementation(strategy)
                strategy_admin = admin.getProxyAdmin(strategy)

                table = []
                console.print("[green]=== Admin: {} Strategy ===[green]".format(key))
                table.append(["Strategy Logic", strategy_impl])
                table.append(["Strategy Admin", strategy_admin])

        print(tabulate(table, ["Key", "Value"]))
