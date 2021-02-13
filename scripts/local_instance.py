from helpers.proxy_utils import deploy_proxy
from helpers.gnosis_safe import GnosisSafe, MultisigTxMetadata
import os
from scripts.systems.sushiswap_system import SushiswapSystem
from scripts.systems.digg_system import connect_digg
from scripts.systems.uniswap_system import UniswapSystem
import time

from brownie import *
import decouple
from config.badger_config import badger_config
from helpers.constants import *
from helpers.time_utils import days
from helpers.token_utils import (
    distribute_from_whales,
    distribute_meme_nfts,
    distribute_test_ether,
)
from rich.console import Console
from scripts.deploy.deploy_digg import (
    deploy_digg_with_existing_badger,
    digg_deploy_flow,
    init_prod_digg,
)
from scripts.systems.badger_system import connect_badger
from helpers.registry import token_registry
from config.badger_config import digg_config
console = Console()


def main():
    """
    Connect to badger, distribute assets to specified test user, and keep ganache open.
    Ganache will run with your default brownie settings for mainnet-fork
    """

    # The address to test with
    user = accounts.at(decouple.config("TEST_ACCOUNT"), force=True)

    badger = connect_badger("deploy-final.json", load_deployer=False, load_keeper=False, load_guardian=False)

    console.print("[blue]=== 🦡 Test ENV for account {} 🦡 ===[/blue]".format(user))

    # ===== Transfer test assets to User =====
    distribute_test_ether(user, Wei("10 ether"))
    distribute_test_ether(badger.deployer, Wei("20 ether"))
    distribute_from_whales(user)

    gitcoin_airdrop_root = "0xcd18c32591078dcb6686c5b4db427b7241f5f1209e79e2e2a31e17c1382dd3e2"
    bBadger = badger.getSett("native.badger")

    # ===== Local Setup =====
    airdropLogic = AirdropDistributor.deploy({"from": badger.deployer})
    airdropProxy = deploy_proxy(
        "AirdropDistributor",
        AirdropDistributor.abi,
        airdropLogic.address,
        badger.opsProxyAdmin.address,
        airdropLogic.initialize.encode_input(
            bBadger,
            gitcoin_airdrop_root,
            badger.rewardsEscrow,
            chain.time() + days(7)
        ),
        badger.deployer
    )

    bBadger.transfer(airdropProxy, Wei("10000 ether"), {"from": user})

    airdropProxy.unpause({"from": badger.deployer})
    airdropProxy.openAirdrop({"from": badger.deployer})

    console.print("[blue]Gitcoin Airdrop deployed at {}[/blue]".format(airdropProxy.address))
    console.print("[green]=== ✅ Test ENV Setup Complete ✅ ===[/green]")
    # Keep ganache open until closed
    time.sleep(days(365))

