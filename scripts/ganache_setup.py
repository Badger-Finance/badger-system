import os
import time

from brownie import *
import decouple
from config.badger_config import badger_config
from helpers.constants import *
from helpers.time_utils import days
from helpers.token_utils import distribute_from_whales, distribute_meme_nfts, distribute_test_ether
from rich.console import Console

from scripts.systems.badger_system import connect_badger

console = Console()

def main():
    """
    Connect to badger, distribute assets to specified test user, and keep ganache open.
    Ganache will run with your default brownie settings for mainnet-fork
    """

    # The address to test with
    user = accounts.at(decouple.config("TEST_ACCOUNT"), force=True)

    badger = connect_badger(badger_config.prod_json)

    console.print("[blue]=== 🦡 Test ENV for account {} 🦡 ===[/blue]".format(user))

    distribute_test_ether(user, Wei("10 ether"))
    distribute_from_whales(badger, user)

    # Keep ganache open until closed
    time.sleep(days(365))
        
