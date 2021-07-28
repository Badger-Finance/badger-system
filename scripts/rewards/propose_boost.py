from brownie import *
from assistant.rewards.boost.boost import badger_boost
from assistant.rewards.aws_utils import upload_boosts
from scripts.systems.badger_system import connect_badger
from rich.console import Console

console = Console()


def main():
    badger = connect_badger()
    currentBlock = chain.height
    badgerBoost, boostInfo = badger_boost(badger, currentBlock)

    # upload_boosts(test=True)
