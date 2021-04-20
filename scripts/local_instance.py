from assistant.rewards.rewards_utils import publish_new_root
from helpers.proxy_utils import deploy_proxy
from helpers.gnosis_safe import GnosisSafe, MultisigTxMetadata
import os
from scripts.systems.sushiswap_system import SushiswapSystem
from scripts.systems.badger_system import print_to_file
from scripts.systems.digg_system import connect_digg
from scripts.systems.uniswap_system import UniswapSystem
from scripts.systems.claw_minimal import deploy_claw_minimal
import time

from brownie import *
import decouple
from config.badger_config import (
    badger_config,
    sett_config,
    digg_config,
    claw_config
)
from helpers.constants import *
from helpers.time_utils import days
from helpers.token_utils import (
    distribute_from_whales,
    distribute_meme_nfts,
    distribute_test_ether,
)
from rich.console import Console
from scripts.systems.badger_system import connect_badger
console = Console()

params = {
    'publishTestRoot': True,
    'root': "0x34f1add21595c8c2d60a19095a047b4764aee553991ec935d914f367c00ecbff",
    'contentHash': "0x34f1add21595c8c2d60a19095a047b4764aee553991ec935d914f367c00ecbff"
}


def main():
    """
    Connect to badger, distribute assets to specified test user, and keep ganache open.
    Ganache will run with your default brownie settings for mainnet-fork
    """

    # The address to test with
    user = accounts.at(decouple.config("TEST_ACCOUNT"), force=True)
    badger = connect_badger()
    distribute_from_whales(user)

    console.print("[green]=== ✅ Test ENV Setup Complete ✅ ===[/green]")
    # Keep ganache open until closed
    time.sleep(days(365))
