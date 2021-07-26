from assistant.rewards.boost import boost
from brownie import *
from scripts.systems.badger_system import connect_badger
from rich.console import Console

console = Console()


def main():
    badger = connect_badger()
    currentBlock = chain.height
    badgerBoost = boost(badger, currentBlock)
    upload_boosts(test=False)
