from brownie import *
from rich.console import Console
from config.badger_config import badger_config
from helpers.sett.SnapshotManager import SnapshotManager
from scripts.systems.badger_system import connect_badger
from tabulate import tabulate
from scripts.systems.sushiswap_system import SushiswapSystem

console = Console()


def main():
    badger = connect_badger()
    table = []
    sushi = SushiswapSystem()
    numPools = sushi.chef.poolLength()
    for i in range(0, numPools):
        poolInfo = sushi.chef.poolInfo(i)
        table.append([poolInfo[0],poolInfo[1],poolInfo[2],poolInfo[3]])
    
    print(tabulate(table, headers=["lpToken", "allocPoint", "lastRewardBlock", "accSushiPerShare"]))
    


