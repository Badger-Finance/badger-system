import time

from brownie import *
import decouple

from helpers.constants import *
from helpers.time_utils import days
from helpers.token_utils import distribute_from_whales
from rich.console import Console
from scripts.systems.badger_system import connect_badger

console = Console()

params = {
    "publishTestRoot": True,
    "root": "0x34f1add21595c8c2d60a19095a047b4764aee553991ec935d914f367c00ecbff",
    "contentHash": "0x34f1add21595c8c2d60a19095a047b4764aee553991ec935d914f367c00ecbff",
}


def main():
    """
    Connect to badger, distribute assets to specified test user, and keep ganache open.
    Ganache will run with your default brownie settings for mainnet-fork
    """

    # The address to test with
    user = accounts.at(decouple.config("TEST_ACCOUNT"), force=True)
    badger = connect_badger()

    tree = badger.badgerTree
    newLogic = BadgerTreeV2.at("0x603ad0e0e0fc873371bd1d98f06e567a8c752ac8")
    ops = accounts.at(badger.opsMultisig, force=True)
    badger.opsProxyAdmin.upgrade(tree, newLogic, {"from": ops})

    distribute_from_whales(user)

    console.print("[green]=== ✅ Test ENV Setup Complete ✅ ===[/green]")
    # Keep ganache open until closed
    time.sleep(days(365))
