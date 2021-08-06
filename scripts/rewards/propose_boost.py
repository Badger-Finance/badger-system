from brownie import *
from assistant.rewards.boost.boost import badger_boost
from assistant.rewards.aws.boost import add_user_data
from scripts.systems.badger_system import connect_badger
from rich.console import Console

console = Console()


def main():
    badger = connect_badger()
    currentBlock = chain.height
    boostData = badger_boost(badger, currentBlock)
    add_user_data(test=True, userData=boostData)
