import time

from brownie import *
from config.badger_config import badger_config
from helpers.constants import *
from helpers.time_utils import days
from helpers.token_utils import distribute_from_whales, distribute_meme_nfts
from rich.console import Console

from scripts.systems.badger_system import connect_badger

console = Console()

def main():
    """
    Connect to badger, distribute assets to specified test user, and keep ganache open.
    Ganache will run with your default brownie settings for mainnet-fork
    """

    # The address to test with
    user = ""

    badger = connect_badger(badger_config.prod_json)
    distribute_from_whales(badger, user)
    distribute_meme_nfts(badger, user)

    # Keep ganache open until closed
    time.sleep(days(365))
        
