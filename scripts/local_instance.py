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

    badger = connect_badger("deploy-test-digg.json", load_deployer=True, load_keeper=True, load_guardian=True)
    digg = connect_digg("deploy-test-digg.json")
    digg.token = digg.uFragments

    badger.add_existing_digg(digg)

    console.print("[blue]=== 🦡 Test ENV for account {} 🦡 ===[/blue]".format(user))

    distribute_test_ether(user, Wei("10 ether"))
    distribute_test_ether(badger.deployer, Wei("20 ether"))
    distribute_from_whales(user)

    wbtc = interface.IERC20(token_registry.wbtc)

    assert wbtc.balanceOf(user) >= 200000000
    init_prod_digg(badger, user)

    accounts.at(digg.daoDiggTimelock, force=True)
    digg.token.transfer(user, 20000000000, {"from": digg.daoDiggTimelock})

    digg_liquidity_amount = 1000000000
    wbtc_liquidity_amount = 100000000

    assert digg.token.balanceOf(user) >= digg_liquidity_amount * 2
    assert wbtc.balanceOf(user) >= wbtc_liquidity_amount * 2

    uni = UniswapSystem()
    wbtc.approve(uni.router, wbtc_liquidity_amount, {"from": user})
    digg.token.approve(uni.router, digg_liquidity_amount, {"from": user})
    uni.router.addLiquidity(
        digg.token,
        wbtc,
        digg_liquidity_amount,
        wbtc_liquidity_amount,
        digg_liquidity_amount,
        wbtc_liquidity_amount,
        user,
        chain.time() + 1000,
        {"from": user},
    )

    sushi = SushiswapSystem()
    wbtc.approve(sushi.router, wbtc_liquidity_amount, {"from": user})
    digg.token.approve(sushi.router, digg_liquidity_amount, {"from": user})
    sushi.router.addLiquidity(
        digg.token,
        wbtc,
        digg_liquidity_amount,
        wbtc_liquidity_amount,
        digg_liquidity_amount,
        wbtc_liquidity_amount,
        user,
        chain.time() + 1000,
        {"from": user},
    )

    console.print("[green]=== ✅ Test ENV Setup Complete ✅ ===[/green]")
    # Keep ganache open until closed
    time.sleep(days(365))

